"""Causal, deterministic repair-state PI. No task execution or learned summarizer.

Completed tool messages are journaled at the proxy boundary, where they are
already Actor-visible. We never read the verifier or infer a successful command.
"""
import ast
import difflib
import hashlib
import json
import re


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def build_snapshot(raw, context=3):
    files = sorted(raw["files"], key=lambda f: f["path"])
    identity = [{k: v for k, v in f.items() if k not in {"old_source", "current_source"}} for f in files]
    return {**raw, "state_hash": digest([raw["baseline_sha"], identity]),
            "changed_files": [f["path"] for f in files], "parse_failure_count": 0,
            "pi_format": "repair_state_v2"}


def units(item):
    """Whole unified hunks with bounded local AST context; removed text is old."""
    path = item["path"]
    if item["kind"] != "text":
        return [f"FILE {json.dumps(path)} status={item['status']} kind={item['kind']} (source unavailable)\n"], [], False
    old = (item.get("old_source") or "").splitlines()
    new = (item.get("current_source") or "").splitlines()
    hunks = []
    for group in difflib.SequenceMatcher(None, old, new, autojunk=False).get_grouped_opcodes(3):
        a, b = group[0][1], group[-1][2]
        c, d = group[0][3], group[-1][4]
        lines = [f"FILE {json.dumps(path)} status={item['status']}",
                 f"@@ old {a+1}:{b} current {c+1}:{d} @@"]
        for tag, i, j, k, l in group:
            if tag == "equal":
                lines.extend(" " + s for s in new[k:l])
            else:
                if tag in {"delete", "replace"}: lines.extend("-" + s for s in old[i:j])
                if tag in {"insert", "replace"}: lines.extend("+" + s for s in new[k:l])
        hunks.append("\n".join(lines) + "\n")
    contexts = []
    failed = False
    if path.endswith(".py") and new:
        try:
            tree = ast.parse("\n".join(new))
            changed = set()
            for tag, _, _, k, l in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
                if tag != "equal": changed.update(range(k+1, max(l, k+1)+1))
            referenced = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and getattr(node, "lineno", -1) in changed:
                    referenced.add(node.id)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    enclosing = any(node.lineno <= line <= node.end_lineno for line in changed)
                    if enclosing or (node in tree.body and node.name in referenced):
                        # Exact source signature, including multiline signatures.
                        end = node.body[0].lineno - 1 if node.body else node.lineno
                        end = max(node.lineno, min(end, node.lineno + 5))
                        contexts.append(f"CONTEXT {json.dumps(path)} current:{node.lineno}-{end}\n" +
                                        "\n".join(new[node.lineno-1:end]) + "\n")
                elif isinstance(node, (ast.Import, ast.ImportFrom)) and node in tree.body:
                    names = {a.asname or a.name.split('.')[0] for a in node.names}
                    if names & referenced:
                        contexts.append(f"IMPORT {json.dumps(path)} current:{node.lineno}\n" +
                                        "\n".join(new[node.lineno-1:node.end_lineno]) + "\n")
        except (SyntaxError, ValueError, RecursionError):
            failed = True
    return hunks, list(dict.fromkeys(contexts)), failed


def _fit_units(groups, tokenizer, limit):
    """Round-robin complete units. Oversized hunks become explicitly partial lines."""
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
    selected, used, omitted, partial = [], 0, 0, 0
    width = max((len(g) for g in groups), default=0)
    for index in range(width):
        for group in groups:
            if index >= len(group): continue
            unit = group[index]
            ids = encode(unit)
            if used + len(ids) <= limit:
                selected.append(unit); used += len(ids)
                continue
            # Retain the file/range headers and whole lines, never a silent prefix.
            lines = unit.splitlines(keepends=True)
            marker = "[PARTIAL UNIT: remaining lines omitted]\n"
            candidate = ""
            for line in lines:
                if len(encode(line)) > 256:
                    # No unsafe tokenizer slicing: drop a long source line explicitly.
                    line = "[LONG SOURCE LINE OMITTED]\n"
                if used + len(encode(candidate + line + marker)) > limit: break
                candidate += line
            if len(candidate.splitlines()) >= 3:
                selected.append(candidate + marker)
                used += len(encode(candidate + marker)); partial += 1
            omitted += 1
    # Concatenation can change tokenization; budget the actual serialized section.
    text = "".join(selected)
    while len(encode(text)) > limit and selected:
        selected.pop(); omitted += 1; text = "".join(selected)
    return text, omitted, partial


def completed_evidence(messages, journal, code_hash):
    """Journal exact incoming completed tool observations, not future SDK state.

    No execution-boundary snapshot exists here: freshness is unknown on arrival,
    and explicitly stale after an observed code change. Never claim fresh tests.
    """
    calls = {}
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                calls.setdefault(call.get("id"), []).append(call.get("function") or {})
    for message in messages:
        if message.get("role") != "tool": continue
        key = digest(message)
        if key in journal["seen"]: continue
        journal["seen"].add(key)
        matches = calls.get(message.get("tool_call_id"), [])
        function = matches[0] if len(matches) == 1 else {}
        content = message.get("content")
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=True)
        # Only explicit structured fields establish an exit code. Free text can
        # contain echoed commands/errors and is not an authoritative exit status.
        exit_code = "unknown"
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                value = obj.get("exit_code", obj.get("return_code"))
                if isinstance(value, int) and not isinstance(value, bool): exit_code = value
        except (ValueError, TypeError): pass
        event = {"sequence": len(journal["events"]), "message_hash": key,
                 "tool_call_id": message.get("tool_call_id"), "tool": function.get("name", "unknown"),
                 "code_hash_at_observation": code_hash, "exit_code": exit_code,
                 "status": "completed_observation", "freshness": "unknown",
                 "test_report": "unknown"}
        summaries = re.findall(r"\b\d+ (?:passed|failed|errors?|skipped|xfailed|xpassed)\b", text)
        if summaries and re.search(r"(?:pytest|test)", function.get("arguments", ""), re.I):
            event["test_report"] = ", ".join(summaries[-6:])
            journal["latest_test"] = event
        journal["events"].append(event)
    latest = dict(journal["events"][-1]) if journal["events"] else {"status": "none", "exit_code": "unknown"}
    test = journal.get("latest_test")
    if test:
        latest["test_report"] = test["test_report"]
        latest["test_freshness"] = "stale" if test["code_hash_at_observation"] != code_hash else "unknown"
    if latest.get("code_hash_at_observation") not in {None, code_hash}: latest["freshness"] = "stale"
    return latest


def serialize(snapshot, tokenizer, session, messages, *, logical_call_id, output_limit=None):
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
    state = session.setdefault("repair_pi", {"versions": {}, "previous_files": {},
                                           "journal": {"seen": set(), "events": []}})
    code_hash = snapshot["state_hash"]
    versions = state["versions"]
    versions.setdefault(code_hash, len(versions) + 1)
    version = versions[code_hash]
    files = snapshot["files"]
    identities = {f["path"]: digest(f) for f in files}
    previous = state["previous_files"]
    ordered = sorted(files, key=lambda f: (previous.get(f["path"]) == identities[f["path"]], f["path"]))
    restored_paths = sorted(set(previous) - set(identities))
    hunk_groups = [[f"REVERTED {json.dumps(path)}: current equals prepared baseline\n"] for path in restored_paths]
    context_groups, parse_failures = [], 0
    for item in ordered:
        hunks, context, failed = units(item)
        hunk_groups.append(hunks); context_groups.append(context); parse_failures += failed
    diff, omitted, partial = _fit_units(hunk_groups, tokenizer, 1408)
    context, omitted_context, _ = _fit_units(context_groups, tokenizer, 384)
    reverted = len(set(previous) - set(identities))
    header = (f"[REPAIR_STATE v{version}: supersedes earlier code state; baseline->current]\n"
              f"files={len(files)} reverted_files={reverted} omitted_units={omitted} partial_units={partial} "
              f"omitted_context={omitted_context} parse_errors={parse_failures}\n")
    footer = "[/REPAIR_STATE]\n"
    if len(encode(header + footer)) > 128:
        header = (f"[REPAIR v{version} supersedes prior; old->current]\n"
                  f"files={len(files)} reverted={reverted} omitted={omitted} partial={partial} ctx_omit={omitted_context} parse={parse_failures}\n")
    if len(encode(header + footer)) > 128: raise ValueError("PI manifest exceeds budget")
    code = header + diff + context + footer
    if len(encode(code)) > 1920: raise ValueError("PI code capsule exceeds budget")
    event = completed_evidence(messages, state["journal"], code_hash)
    status = (f"[EXEC observed_code=v{version} status={event['status']} exit={event['exit_code']} "
              f"freshness={event.get('freshness', 'unknown')} calls_completed={session.get('num_calls', 0)} "
              f"generated_tokens={session.get('total_completion_tokens', 0)} next_output_limit={output_limit or 'unknown'} "
              f"test_report={event.get('test_report', 'unknown')} test_freshness={event.get('test_freshness', 'unknown')}]\n")
    if len(encode(status)) > 128:
        status = (f"[EXEC observed_code=v{version} status={event['status']} exit={event['exit_code']} "
                  "freshness=unknown omitted=true]\n")
    if len(encode(status)) > 128: raise ValueError("PI execution line exceeds budget")
    state["previous_files"] = identities
    return {"pi_format": "repair_state_v2", "code_state_hash": code_hash,
            "pi_insertion_key": str(logical_call_id), "code_version": version,
            "code_ids": encode(code), "execution_ids": encode(status),
            "pi_ids": encode(code) + encode(status), "pi_text": code + status,
            "pi_raw_tokens": len(encode(code)) + len(encode(status)),
            "pi_truncated": bool(omitted or omitted_context), "parse_failure_count": parse_failures,
            "execution_evidence": event}
