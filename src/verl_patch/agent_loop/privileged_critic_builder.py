"""Construct the critic view from exact Actor tokens and pre-generation records."""
import hashlib
import json
import os
from pathlib import Path


def message_key(message):
    return hashlib.sha256(json.dumps(message, sort_keys=True, ensure_ascii=True, default=str).encode()).hexdigest()


def _expand_verified_tool_splits(old_records, old_messages, new_messages):
    """Recognize lossless SDK splitting of one multi-tool reply, never fuzzy-match."""
    old_assistants = [m for m in old_messages if m.get("role") == "assistant"]
    incoming = [m for m in new_messages if m.get("role") == "assistant"]
    expanded = []
    for record in old_records:
        source_key = record.get("message_key")
        originals = [m for m in old_assistants if message_key(m) == source_key]
        candidates = []
        if len(originals) == 1:
            original = originals[0]
            calls = original.get("tool_calls")
            if isinstance(calls, list) and len(calls) > 1:
                # Require unique call identities and an exact ordered partition.
                ids = [c.get("id") for c in calls]
                if all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids):
                    for start in range(len(incoming)):
                        consumed, parts = 0, []
                        for message in incoming[start:]:
                            part = message.get("tool_calls")
                            if not isinstance(part, list) or not part:
                                break
                            expected = dict(original)
                            expected["content"] = original.get("content") if not parts else ""
                            expected["tool_calls"] = calls[consumed:consumed + len(part)]
                            if message != expected:
                                break
                            consumed += len(part)
                            parts.append(message_key(message))
                            if consumed == len(calls):
                                if len(parts) > 1:
                                    candidates.append(parts)
                                break
        if len(candidates) > 1:
            raise RuntimeError("PI history join ambiguous: repeated tool split")
        if candidates:
            for index, key in enumerate(candidates[0]):
                rec = dict(record)
                rec.update(message_key=key, source_message_key=source_key,
                           verified_tool_split_index=index,
                           verified_tool_split_count=len(candidates[0]))
                expanded.append(rec)
        else:
            expanded.append(record)
    return expanded


def remap_rebuilt_records(old_records, assistant_spans, *, old_messages=None, new_messages=None):
    """Join retained assistant messages in monotonic call order; fail on unknown turns."""
    if old_messages is not None and new_messages is not None:
        old_records = _expand_verified_tool_splits(old_records, old_messages, new_messages)
    result, cursor = [], 0
    for key, start, end in assistant_spans:
        if sum(r.get("message_key") == key for r in old_records[cursor:]) > 1:
            raise RuntimeError("PI history join ambiguous: repeated identical assistant messages")
        while cursor < len(old_records) and old_records[cursor].get("message_key") != key:
            cursor += 1
        if cursor == len(old_records):
            raise RuntimeError("PI cannot causally map a rewritten historical assistant message")
        rec = dict(old_records[cursor])
        rec.update(actor_response_start_abs=start, actor_response_end_abs=end, remapped=True)
        result.append(rec)
        cursor += 1
    return result


def interleave(actor_ids, prompt_len, response_mask, records, *,
               total_pi_budget=None, tokenizer=None, budget_stats=None):
    """Return critic ids, pre-token gather positions, and PI-only token mask."""
    if prompt_len <= 0 or len(actor_ids) != prompt_len + len(response_mask):
        raise ValueError("Actor prompt/response shape mismatch")
    n = len(actor_ids)
    events, covered = {}, [False] * len(response_mask)
    last_end = prompt_len
    for record in records:
        start, end = record["actor_response_start_abs"], record["actor_response_end_abs"]
        if start >= n:
            continue  # Existing baseline response truncation; no future PI inserted.
        end = min(end, n)
        if not (prompt_len <= start < end <= n) or start < last_end:
            raise ValueError("PI call spans overlap or precede the Actor response")
        if not record.get("valid", True):
            raise ValueError("Invalid PI capture")
        last_end = end
        events[start] = record
        for k in range(start - prompt_len, end - prompt_len):
            covered[k] = True
    if any(mask and not ok for mask, ok in zip(response_mask, covered, strict=True)):
        raise ValueError("Actor action tokens have no pre-generation PI record")
    critic, mapping, pi_mask = [], [], []
    tail, remaining, exhausted = [], None, False
    stats = {"pi_tokens_before": 0, "pi_tokens_after": 0,
             "limited_states": 0, "omitted_later_states": 0}
    if total_pi_budget is not None:
        if tokenizer is None:
            raise ValueError("Total PI budget requires the PI tokenizer")
        tail = tokenizer.encode(
            "\n[TRUNCATED_BY_TOTAL_PI_BUDGET: later PI omitted]\n"
            "[PI EXHAUSTED: no later repair state represented]\n", add_special_tokens=False)
        if total_pi_budget < len(tail):
            raise ValueError("Total PI budget cannot hold its explicit exhaustion marker")
        # Reserve a single exhaustion marker. The fixed quota never depends on
        # final Actor length or on future state count/content.
        remaining = total_pi_budget - len(tail)
    previous_state = None
    previous_code = None
    for offset, token in enumerate(actor_ids):
        record = events.get(offset)
        if record is not None and record.get("pi_insertion_key", record["state_hash"]) != previous_state:
            pi_ids = list(record.get("pi_ids", []))
            if record.get("pi_format") == "repair_state_v2":
                code_hash = record["code_state_hash"]
                pi_ids = ([] if code_hash == previous_code else list(record["code_ids"])) + list(record["execution_ids"])
                previous_code = code_hash
            stats["pi_tokens_before"] += len(pi_ids)
            if remaining is not None:
                if exhausted and pi_ids:
                    stats["omitted_later_states"] += 1
                    pi_ids = []
                elif len(pi_ids) > remaining:
                    if "pi_text" not in record:
                        raise ValueError("Cannot mark total-budget truncation without PI text")
                    if record.get("pi_format") == "repair_state_v2":
                        # Never cut inside a repair hunk or label a missing capsule unchanged.
                        pi_ids = tail
                    else:
                        header, separator, body = record["pi_text"].partition("--- ENTITY ---\n")
                        marked_text = header.replace("truncated: false", "truncated: true", 1) + separator + body
                        marked_ids = tokenizer.encode(marked_text, add_special_tokens=False)
                        pi_ids = marked_ids[:remaining] + tail
                    stats["limited_states"] += 1
                    remaining, exhausted = 0, True
                else:
                    remaining -= len(pi_ids)
            stats["pi_tokens_after"] += len(pi_ids)
            critic.extend(pi_ids)
            pi_mask.extend([1] * len(pi_ids))
            previous_state = record.get("pi_insertion_key", record["state_hash"])
        if offset >= prompt_len:
            mapping.append(len(critic) - 1)
        critic.append(token)
        pi_mask.append(0)
    if any(i < 0 for i in mapping):
        raise ValueError("Missing pre-token context")
    if budget_stats is not None:
        budget_stats.update(stats)
    return critic, mapping, pi_mask


def prepare_critic_view(batch_td, *, tokenizer=None, audit_path=None):
    """Replace only an isolated TensorDict's model inputs; preserve the loss timeline."""
    import torch
    from verl.workers.utils.padding import left_right_2_no_padding

    records = batch_td.get("pi_call_records", None)
    if records is None:
        return left_right_2_no_padding(batch_td)
    inputs, mappings, pi_masks, audits = [], [], [], []
    sequence_limit = int(os.environ.get("PI_CRITIC_MAX_SEQ_TOKENS", "245760"))
    bounded = os.environ.get("PI_TOTAL_BUDGET_ENABLE", "0") == "1"
    actor_reserved = int(os.environ.get("PI_ACTOR_RESERVED_TOKENS", "73728"))
    total_pi_budget = sequence_limit - actor_reserved if bounded else None
    for i in range(batch_td.batch_size[0]):
        actor = batch_td["input_ids"][i][batch_td["attention_mask"][i].bool()].tolist()
        prompt_width = batch_td["prompts"].shape[1]
        plen = int(batch_td["attention_mask"][i, :prompt_width].sum())
        rlen = len(actor) - plen
        mask = batch_td["response_mask"][i, :rlen].tolist()
        recs = records[i]
        if hasattr(recs, "data"):
            recs = recs.data
        # Empty/dropped rows contain no sampled action. Still return Actor-shape values.
        if bounded and len(actor) > actor_reserved:
            raise ValueError("Actor exceeds fixed reserved length; refusing to truncate Actor")
        audit = {"actor_tokens": len(actor)}
        ids, gather, p_mask = interleave(actor, plen, mask, recs or [],
                                        total_pi_budget=total_pi_budget,
                                        tokenizer=tokenizer, budget_stats=audit)
        audit["critic_tokens"] = len(ids)
        audits.append(audit)
        inputs.append(ids)
        mappings.append(gather)
        pi_masks.append(p_mask)
    device = batch_td["input_ids"].device
    width = max(map(len, inputs))
    if width > sequence_limit:
        raise RuntimeError("PI critic sequence exceeds safety limit; Actor tokens were preserved")
    if audit_path is not None and bounded:
        path = Path(audit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"sequence_limit": sequence_limit,
                                    "actor_reserved": actor_reserved,
                                    "total_pi_budget": total_pi_budget,
                                    "rows": audits}, indent=2))
    response_width = batch_td["response_mask"].shape[1]
    critic_ids = torch.zeros((len(inputs), width), dtype=torch.long, device=device)
    attention = torch.zeros_like(critic_ids)
    pi_mask = torch.zeros_like(critic_ids)
    gather = torch.full((len(inputs), response_width), -1, dtype=torch.long, device=device)
    for i, (ids, indices, p_mask) in enumerate(zip(inputs, mappings, pi_masks, strict=True)):
        critic_ids[i, :len(ids)] = torch.tensor(ids, device=device)
        attention[i, :len(ids)] = 1
        pi_mask[i, :len(ids)] = torch.tensor(p_mask, device=device)
        gather[i, :len(indices)] = torch.tensor(indices, device=device)
    batch_td["input_ids"] = critic_ids
    batch_td["attention_mask"] = attention
    batch_td["position_ids"] = attention.cumsum(-1).sub(1).clamp_min(0)
    batch_td["critic_value_gather_indices"] = gather
    # PI tokens are absent from response_mask/loss_mask/rewards, by construction.
    batch_td["critic_pi_mask"] = pi_mask
    return left_right_2_no_padding(batch_td)


def batch_pi_metrics(batch):
    records = batch.non_tensor_batch.get("pi_call_records")
    if records is None:
        return {}
    all_records = [r for row in records for r in (row or [])]
    count = max(1, len(all_records))
    insertions, tokens, changes = 0, 0, 0
    for row in records:
        previous = None
        previous_code = None
        for record in row or []:
            if record.get("pi_insertion_key", record["state_hash"]) != previous:
                insertions += 1
                if record.get("pi_format") == "repair_state_v2":
                    tokens += len(record["execution_ids"])
                    if record["code_state_hash"] != previous_code:
                        tokens += len(record["code_ids"]); changes += 1
                    previous_code = record["code_state_hash"]
                else:
                    tokens += len(record.get("pi_ids", [])); changes += 1
                previous = record.get("pi_insertion_key", record["state_hash"])
    capture_ms = [(r["captured_at_end_ns"] - r["captured_at_start_ns"]) / 1e6 for r in all_records]
    return {"pi/enabled": 1., "pi/captured_calls": float(len(all_records)),
            "pi/captured_state_changes": float(changes), "pi/captured_insertions": float(insertions), "pi/captured_dedup_tokens": float(tokens),
            "pi/changed_files_mean": sum(len(r["changed_files"]) for r in all_records) / count,
            "pi/truncated_fraction": sum(bool(r.get("pi_truncated")) for r in all_records) / count,
            "pi/parse_failure_fraction": sum(r.get("parse_failure_count", 0) > 0 for r in all_records) / count,
            "pi/capture_ms_mean": sum(capture_ms) / count, "pi/capture_ms_max": max(capture_ms, default=0.)}


def gather_critic_values(tensor, data):
    """Gather full-sequence values to the original padded Actor response shape."""
    import torch
    values = tensor.values() if tensor.is_nested else tensor
    indices = data["critic_value_gather_indices"]
    if indices.is_nested:
        indices = indices.to_padded_tensor(-1)
    ids = data["input_ids"]
    lengths = ids.offsets().diff() if ids.is_nested else data["attention_mask"].sum(-1)
    if int(lengths.sum()) != values.shape[0]:
        raise ValueError("Critic packed value lengths mismatch")
    offsets = torch.cat([lengths.new_zeros(1), lengths.cumsum(0)[:-1]])
    valid = indices >= 0
    if bool((valid & (indices >= lengths[:, None])).any()):
        raise ValueError("Out-of-sequence critic gather index")
    absolute = indices.clamp_min(0) + offsets[:, None]
    result = values[absolute]
    result = result * valid.to(result.dtype)
    return result
