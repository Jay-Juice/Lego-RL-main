"""Actual CPU proxy + Qwen + builder; scripted generation, synthetic workspace.

This is not a Docker/Harbor probe, Actor rollout, GPU update or training gate.
"""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


async def exercise(tokenizer, enabled):
    import numpy as np
    from harbor_patch.privileged_state import registry
    from verl.workers.rollout.replica import TokenOutput
    from verl_patch.agent_loop.vllm_chat_completion_proxy import (
        _VLLMChatCompletionsProxy, _proxy_error_from_exception)
    from verl_patch.agent_loop.privileged_critic_builder import interleave
    from dynamic_runtime_r6 import Capture, CACHE, CONTEXT
    from dynamic_session_r6_r2 import R6DynamicSessionR2

    os.environ['PI_ENABLE'] = '1' if enabled else '0'
    sid = 'r6-proxy-enabled' if enabled else 'r6-proxy-control'
    issue = 'PRIVATE_ISSUE_SENTINEL function f returns an integer'
    initial = dict(files={'a.py': 'def f(x):\n    return x+1\n'}, stable=True, limited=False)
    added = copy.deepcopy(initial)
    added['files']['new.py'] = 'def newly_added(x):\n    return x*7\n'
    edited = copy.deepcopy(added)
    edited['files']['a.py'] = 'def f(x):\n    return x+2\n'
    renamed = copy.deepcopy(edited)
    renamed['files']['renamed.py'] = renamed['files'].pop('new.py')
    syntax = copy.deepcopy(renamed)
    syntax['files']['a.py'] = 'def broken(:\n    pass\n'
    limited = dict(files={}, stable=True, limited=True)
    deleted = dict(files={}, stable=True, limited=False)
    events = [initial, initial, added, edited, renamed, syntax, limited, deleted, initial]
    source = initial
    captures, audit = [], []

    async def scan():
        captures.append(copy.deepcopy(source))
        return source

    capture = Capture(issue, 'synthetic-proxy-task', sid, scan)
    direct = R6DynamicSessionR2(issue, tokenizer, 'synthetic-proxy-task', sid)
    if enabled:
        registry.register(sid, capture.capture)

    class Manager:
        async def generate(self, request_id, prompt_ids, sampling_params):
            audit.append(dict(start=time.time_ns(), ids=list(prompt_ids)))
            if enabled:
                pending = proxy._sessions[sid]['pi_pending_record']
                assert CONTEXT not in pending and CACHE not in pending and 'files' not in pending
                assert issue not in json.dumps(pending)
                assert pending['captured_at_end_ns'] <= audit[-1]['start']
            ids = tokenizer.encode(f'Workspace call {len(audit)}.', add_special_tokens=False)
            routing = np.ones((len(prompt_ids) + len(ids), 2, 1), dtype=np.int32)
            return TokenOutput(token_ids=ids, log_probs=[-0.125]*len(ids),
                               routed_experts=routing, stop_reason='length')

    loop = SimpleNamespace(tokenizer=tokenizer, processor=None, server_manager=Manager(),
                           loop=asyncio.get_running_loop(), apply_chat_template_kwargs={})

    async def template(messages, tools=None, remove_system_prompt=False):
        from verl.utils.chat_template import apply_chat_template, initialize_system_prompt
        ids = apply_chat_template(tokenizer, messages, tools=tools, tokenize=True,
                                  add_generation_prompt=True)
        if remove_system_prompt:
            ids = ids[len(initialize_system_prompt(tokenizer)):]
        return ids

    loop.apply_chat_template = template
    proxy = _VLLMChatCompletionsProxy(loop, 'qwen3_coder', max_consecutive_no_tool=0)
    await proxy.open_session(sid)
    messages = [{'role': 'user', 'content': 'Inspect the workspace.'}]
    records = []
    try:
        for index, source in enumerate(events):
            if index:
                messages.append({'role': 'user', 'content': f'Next observation {index}.'})
            message, *_ = await proxy._generate_assistant_message(
                sid, messages, None, {'temperature': 0.7, 'max_tokens': 16})
            messages.append(message)
            if enabled:
                record = copy.deepcopy(proxy._sessions[sid]['pi_call_records'][-1])
                expected = direct.capture(source, task_uid='synthetic-proxy-task', session_id=sid,
                                          logical_call_id=record['logical_call_id'],
                                          seq=record['state_seq'])
                for key, value in expected.items():
                    assert record[key] == value, (index, key)
                assert len(record['pi_ids']) <= (192 if index == 0 else 128)
                records.append(record)
        if enabled:
            assert records[1]['pi_ids'] == [], 'noop must not consume PI'
            assert any(w['file'] == 'new.py' for w in records[2]['windows']), 'new file invisible'
            assert any(w['file'] == 'renamed.py' for w in records[4]['windows']), 'rename invisible'
            assert records[-1]['pi_ids'], 'rollback must remain visible'
            registry.unregister(sid)
            before = len(audit)
            try:
                await proxy._generate_assistant_message(sid, messages, None, {'max_tokens': 16})
                raise AssertionError('closed session generated')
            except registry.SessionClosedError as exc:
                assert _proxy_error_from_exception(exc).status == 410
            assert len(audit) == before
        meta = await proxy.pop_session(sid)
        assert CACHE not in meta and CONTEXT not in meta
        assert issue not in json.dumps(meta)
        if enabled:
            actor = meta['traj_acc_ids']
            plen = meta['initial_prompt_token_len']
            mask = meta['traj_response_mask']
            critic, mapping, pi_mask = interleave(actor, plen, mask, records,
                                                  total_pi_budget=4096, tokenizer=tokenizer)
            assert [x for x, p in zip(critic, pi_mask) if not p] == actor
            assert len(mapping) == len(mask)
            for i, position in enumerate(mapping):
                assert critic[position+1] == actor[plen+i]
            # Extending with future captures cannot alter any earlier causal context.
            for last in range(1, len(records)):
                end = records[last-1]['actor_response_end_abs']
                short, gather, _ = interleave(actor[:end], plen, mask[:end-plen], records[:last],
                                              total_pi_budget=4096, tokenizer=tokenizer)
                assert short == critic[:len(short)]
                assert gather == mapping[:len(gather)]
            # The actual new-format builder must omit a whole window, never slice it.
            tail = tokenizer.encode('\n[TRUNCATED_BY_TOTAL_PI_BUDGET: later PI omitted]\n'
                                    '[PI EXHAUSTED: no later repair state represented]\n',
                                    add_special_tokens=False)
            small, _, small_mask = interleave(actor, plen, mask, records,
                                               total_pi_budget=len(tail)+1, tokenizer=tokenizer)
            assert [x for x,p in zip(small, small_mask) if p] == tail
            assert interleave([1, 2], 1, [0], [])[0] == [1, 2]
            try:
                interleave([1, 2], 1, [1], [])
                raise AssertionError('uncovered action accepted')
            except ValueError as exc:
                assert 'no pre-generation' in str(exc)
        return meta, [a['ids'] for a in audit], dict(calls=len(audit), captures=len(captures))
    finally:
        if enabled:
            registry.unregister(sid)
        await proxy.stop()


async def failure_cleanup(tokenizer):
    from verl_patch.agent_loop.vllm_chat_completion_proxy import _VLLMChatCompletionsProxy
    from dynamic_runtime_r6 import CACHE
    # Real pop_session, with a deliberate failing audit destination. No model call.
    loop = SimpleNamespace(tokenizer=tokenizer, processor=None, server_manager=None,
                           loop=asyncio.get_running_loop(), apply_chat_template_kwargs={})
    proxy = _VLLMChatCompletionsProxy(loop, 'qwen3_coder', max_consecutive_no_tool=0)
    sid = 'r6-audit-failure'
    await proxy.open_session(sid)
    meta = proxy._sessions[sid]
    meta[CACHE] = {'private': 'must be released'}
    meta['trajectory_dir'] = '/dev/null/invalid-audit-directory'
    meta['pi_error'] = 'scripted audit failure'
    try:
        try:
            await proxy.pop_session(sid)
            raise AssertionError('audit failure did not occur')
        except OSError:
            pass
        assert CACHE not in meta and sid not in proxy._sessions
    finally:
        await proxy.stop()


async def main():
    from transformers import AutoTokenizer
    import verl_patch.agent_loop.vllm_chat_completion_proxy as proxy_module
    import verl_patch.agent_loop.privileged_critic_builder as builder_module
    assert Path(proxy_module.__file__).resolve() == ROOT/'runtime/vllm_chat_completion_proxy.py'
    assert Path(builder_module.__file__).resolve() == ROOT/'runtime/privileged_critic_builder.py'
    tokenizer = AutoTokenizer.from_pretrained(os.environ['PI_PROBE_MODEL'], local_files_only=True)
    enabled, prompts_a, details = await exercise(tokenizer, True)
    control, prompts_b, _ = await exercise(tokenizer, False)
    keys = ['traj_acc_ids', 'initial_prompt_token_len', 'traj_response_mask',
            'traj_response_logprobs', 'traj_response_routing']
    for key in keys:
        assert enabled[key] == control[key], key
    assert prompts_a == prompts_b
    assert any(value is not None for value in enabled['traj_response_routing'])
    await failure_cleanup(tokenizer)
    result = dict(status='passed', actual_proxy=True, actual_qwen_tokenizer=True,
                  synthetic_workspace=True, scripted_generation=True, actual_actor_rollout=False,
                  harbor=False, gpu=False, optimizer=False, **details,
                  direct_frozen_outputs_exact=True, actor_invariance=keys+['manager_prompt_ids'],
                  closed_410_no_generation=True, private_metadata_cleanup=True,
                  cleanup_before_failed_audit=True, causal_pretoken_gather=True,
                  new_format_no_partial_window=True, empty_row_and_missing_action_checked=True,
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [ROOT/'runtime/vllm_chat_completion_proxy.py',
                                           ROOT/'runtime/remote_docker.py',
                                           ROOT/'runtime/privileged_critic_builder.py', Path(__file__)]})
    out = ROOT/'reports/ONLINE_PROXY_R6_CONTRACTS.json'
    assert not out.exists(), 'preserve existing evidence'
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    asyncio.run(main())
