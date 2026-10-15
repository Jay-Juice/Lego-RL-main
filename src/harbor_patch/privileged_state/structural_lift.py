import ast
import difflib
import hashlib
import json


def scopes(source):
    tree = ast.parse(source)
    result = []

    def visit(node, parents):
        for child in ast.iter_child_nodes(node):
            enclosing = isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            names = parents
            if enclosing:
                start = min([child.lineno] + [d.lineno for d in child.decorator_list])
                names = parents + [child.name]
                result.append({"qualname": ".".join(names), "start_line": start,
                               "end_line": child.end_lineno,
                               "kind": "class" if isinstance(child, ast.ClassDef) else
                               "async_function" if isinstance(child, ast.AsyncFunctionDef) else "function"})
            visit(child, names)
    visit(tree, [])
    return result


def lift(item, context=20):
    path = item["path"]
    if item["kind"] != "text":
        return [{k: v for k, v in item.items() if k not in {"old_source", "current_source"}}], 0
    current, old = item["current_source"] or "", item["old_source"] or ""
    lines, old_lines = current.splitlines(), old.splitlines()
    ops = [x for x in difflib.SequenceMatcher(None, old_lines, lines, autojunk=False).get_opcodes() if x[0] != "equal"]
    parse_failed = 0
    entities = []
    try:
        entities = scopes(current) if path.endswith(".py") else []
    except (SyntaxError, ValueError, RecursionError):
        parse_failed = 1
    selected = {}
    try:
        old_entities = scopes(old) if path.endswith(".py") else []
    except (SyntaxError, ValueError, RecursionError):
        old_entities = []
    current_names = {e["qualname"] for e in entities}
    for tag, i1, i2, j1, j2 in ops:
        # Removed scopes get metadata only, never stale source as current source.
        for ent in old_entities:
            if ent["qualname"] not in current_names and ent["start_line"] <= i2 and ent["end_line"] >= i1 + 1:
                key = ("removed", ent["qualname"])
                selected[key] = dict(ent, path=path, status="removed", current_source=None, changed_ranges=[])
        # For deletion-only hunks use the adjacent surviving line if it lies in a scope.
        first = min(j1 + 1, len(lines)) if lines else 0
        last = max(first, j2)
        for line in range(first, last + 1):
            matches = [e for e in entities if e["start_line"] <= line <= e["end_line"]]
            ent = min(matches, key=lambda e: (e["end_line"] - e["start_line"], -e["start_line"])) if matches else None
            if ent:
                key = (ent["start_line"], ent["end_line"], ent["qualname"])
                if key not in selected:
                    selected[key] = dict(ent, path=path, status=item["status"],
                                         current_source="\n".join(lines[ent["start_line"] - 1:ent["end_line"]]), changed_ranges=[])
                selected[key]["changed_ranges"].append([first, last])
            else:
                start, end = max(0, j1 - context), min(len(lines), max(j2, j1 + 1) + context)
                key = ("region", start, end)
                selected[key] = {"path": path, "kind": "module_region", "qualname": "<module>",
                                 "status": item["status"], "start_line": start + 1, "end_line": end,
                                 "parse_status": "syntax_error" if parse_failed else "ok",
                                 "current_source": "\n".join(lines[start:end]),
                                 "changed_ranges": [[first, last]]}
    return sorted(selected.values(), key=lambda e: (e["start_line"], e["qualname"], e["status"])), parse_failed


def build_snapshot(raw, context=20):
    entities, failures = [], 0
    for item in raw["files"]:
        lifted, failed = lift(item, context)
        entities.extend(lifted)
        failures += failed
    canonical = {"baseline_sha": raw["baseline_sha"], "files": [
        {k: v for k, v in f.items() if k not in {"old_source", "current_source"}} for f in raw["files"]]}
    state_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    return {**{k: v for k, v in raw.items() if k != "files"}, "state_hash": state_hash,
            "changed_files": [f["path"] for f in raw["files"]], "entities": entities,
            "parse_failure_count": failures}


def serialize(snapshot, tokenizer, max_tokens=1024):
    def text(truncated):
        header = ("[PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\n"
                  f"changed_files: {len(snapshot['changed_files'])}\nentity_count: {len(snapshot['entities'])}\n"
                  f"parse_failures: {snapshot['parse_failure_count']}\ntruncated: {str(truncated).lower()}\n")
        if not snapshot["changed_files"]:
            header += "workspace_delta: empty (prepared buggy state)\n"
        parts = []
        for entity in snapshot["entities"]:
            metadata = {k: v for k, v in entity.items() if k != "current_source"}
            part = "--- ENTITY ---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}"
                                                     for k, v in metadata.items())
            if entity.get("current_source") is not None:
                part += "\ncurrent_source:\n" + entity["current_source"]
            parts.append(part)
        body = "\n".join(parts)
        return header + body + "\n[/PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\n"
    full = text(False)
    ids = tokenizer.encode(full, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return full, ids, len(ids), False
    # Leave a visible truncation marker and close the PI block within the hard budget.
    tail = tokenizer.encode("\n[TRUNCATED]\n[/PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\n", add_special_tokens=False)
    head = tokenizer.encode(text(True), add_special_tokens=False)
    if max_tokens <= len(tail):
        raise ValueError("PI token budget too small")
    ids = head[:max_tokens - len(tail)] + tail
    return tokenizer.decode(ids, skip_special_tokens=False), ids, len(tokenizer.encode(full, add_special_tokens=False)), True
