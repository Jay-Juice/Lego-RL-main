"""Frozen W0 PI transport on archived real Actor tensors; not live rollout.

No selection/generation or label scoring occurs here. Frozen, hash-bound PI is
injected at the first historical call only. Later workspace states are unknown.
"""
import collections
import hashlib
import json
import os
import time
from pathlib import Path

N = Path(__file__).resolve().parents[1]
R = N.parent / 'pi_repair_state_v2_20261015'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    import numpy as np
    import torch
    from transformers import AutoTokenizer
    from verl import DataProto
    from verl_patch.agent_loop import privileged_critic_builder as builder
    from verl.workers.utils.padding import no_padding_2_padding
    torch.set_num_threads(2)
    assert Path(builder.__file__).resolve() == N / 'runtime/privileged_critic_builder.py'
    assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
    out = N / 'logs/trajectory_replay_r7_r2'
    rows = read(R / '.private_location_pi_control_20261022/manifests/P0_FROZEN_607_MANIFEST.json')['rows']
    receipt_path = N / 'reports/entity_evidence_r7/GENERATION_RECEIPT.json'
    receipt = read(receipt_path)
    hashes = {r['uid']: r['SHA'] for r in receipt['rows']}
    assert len(rows) == len(hashes) == 607
    tok = AutoTokenizer.from_pretrained(str(N.parents[1] / 'Qwen3.5-9B'), local_files_only=True)
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row['source_batch_path']].append(row)
    counts = collections.Counter()
    lengths, timings, failures = [], [], []
    whitelist = ('input_ids', 'attention_mask', 'prompts', 'responses', 'response_mask',
                 'position_ids', 'rollout_log_probs', 'old_log_probs')
    started = time.monotonic()
    for batch_path, group in sorted(grouped.items()):
        # Trusted local historical checkpoint container. Only Actor fields below
        # enter the new view; reward/returns/advantages/old PI never do.
        assert {r['batch_sha256'] for r in group} == {sha(Path(batch_path))}, 'batch identity'
        batch = torch.load(batch_path, map_location='cpu', mmap=True, weights_only=False)
        for row in group:
            uid = hashlib.sha256(('icps-coverage:' + row['task_id']).encode()).hexdigest()
            try:
                p = N / '.private_entity_evidence_r7' / (uid + '.json')
                assert sha(p) == hashes[uid], 'frozen PI identity'
                z = read(p)['serialized']['cached1024_8']
                pi = z['pi_ids']
                assert len(pi) <= 1024 and pi == tok.encode(z['pi_text'], add_special_tokens=False)
                i = int(row['row'])
                assert batch['non_tensor']['extra_info'][i]['instance_id'] == row['task_id'], 'task-row identity'
                tensors = {k: batch['tensors'][k][i:i+1].clone() for k in whitelist if k in batch['tensors']}
                saved = {k: v.clone() for k, v in tensors.items()}
                raw = read(Path(row['pi_records_path']))['records']
                records = [dict(actor_response_start_abs=r['actor_response_start_abs'],
                                actor_response_end_abs=r['actor_response_end_abs'],
                                valid=r.get('valid', True), state_hash='replay-' + str(j),
                                pi_format='icps_dynamic_v1', pi_ids=pi if j == 0 else [],
                                pi_text=z['pi_text'] if j == 0 else '') for j, r in enumerate(raw)]
                actor = tensors['input_ids'][0][tensors['attention_mask'][0].bool()].tolist()
                plen = int(tensors['attention_mask'][0, :tensors['prompts'].shape[1]].sum())
                rlen = len(actor) - plen
                mask = tensors['response_mask'][0, :rlen].tolist()
                t = time.monotonic()
                stats = {}
                ids, mapping, pmask = builder.interleave(actor, plen, mask, records,
                    total_pi_budget=172032, tokenizer=tok, budget_stats=stats)
                assert [x for x, m in zip(ids, pmask) if not m] == actor, 'Actor restoration'
                assert [x for x, m in zip(ids, pmask) if m] == pi, 'PI transport loss'
                assert stats['limited_states'] == stats['omitted_later_states'] == 0
                arr = np.empty(1, dtype=object); arr[0] = records
                dp = DataProto.from_dict(tensors, {'pi_call_records': arr})
                view = builder.prepare_critic_view(dp.to_tensordict(), tokenizer=tok)
                assert view['input_ids'].unbind()[0].tolist() == ids, 'actual view differs'
                for k in tensors:
                    assert torch.equal(saved[k], dp.batch[k]), 'Actor changed: ' + k
                assert torch.equal(view['loss_mask'], saved['response_mask']), 'action loss mask changed'
                # Positional witness verifies the actual packed gather and its
                # derivative. This is not a neural value/loss/gradient test.
                values = torch.arange(len(ids), dtype=torch.float32, requires_grad=True)
                got = no_padding_2_padding(values, view)
                assert got[0, :rlen].tolist() == [float(x) for x in mapping]
                assert not bool(got[0, rlen:].any())
                action_mask = tensors['response_mask'].to(got.dtype)
                (got * action_mask).sum().backward()
                expected = torch.zeros_like(values)
                expected.scatter_add_(0, torch.tensor(mapping), action_mask[0, :rlen])
                assert torch.equal(values.grad, expected), 'gather gradient mismatch'
                # Empty PI keeps the historical Actor stream exactly.
                empty = [dict(r, pi_ids=[], pi_text='') for r in records]
                eids, emap, epmask = builder.interleave(actor, plen, mask, empty)
                assert eids == actor and not any(epmask)
                assert emap == list(range(plen - 1, len(actor) - 1))
                # Adding a later call cannot change the earlier input prefix.
                if len(records) > 1:
                    cut = min(records[1]['actor_response_start_abs'], len(actor))
                    if cut > plen:
                        short, _, _ = builder.interleave(actor[:cut], plen, mask[:cut-plen], records[:1])
                        assert ids[:len(short)] == short
                timings.append(time.monotonic() - t)
                lengths.append(dict(actor=len(actor), critic=len(ids), pi=len(pi), calls=len(records)))
                counts['passed'] += 1
            except Exception as exc:
                counts['failed'] += 1
                failures.append(dict(uid=uid, error=type(exc).__name__, message=str(exc)))
            if sum(counts.values()) % 25 == 0:
                print(json.dumps(dict(counts=counts, elapsed=time.monotonic()-started)), flush=True)
        del batch
    (out / 'private_failures.json').write_text(json.dumps(failures, indent=2))
    report = dict(status='pass' if not failures else 'failed', counts=dict(counts),
        source_batches=len(grouped), budget=1024, windows=8,
        frozen_PI_receipt_SHA=sha(receipt_path), builder_SHA=sha(Path(builder.__file__)),
        script_SHA=sha(Path(__file__)),
        actor_tokens_max=max((v['actor'] for v in lengths), default=0),
        critic_tokens_max=max((v['critic'] for v in lengths), default=0),
        PI_tokens_total=sum(v['pi'] for v in lengths),
        calls_total=sum(v['calls'] for v in lengths),
        mean_view_seconds=sum(timings)/max(1,len(timings)), wall_seconds=time.monotonic()-started,
        actual_historical_actor_tensors=True, actual_runtime_builder=True,
        new_model_rollout=False, neural_value_gradient_test=False,
        positional_gather_gradient_test=True, source_snapshot_identity_proven=False,
        later_dynamic_states_tested=False, independent_confirmation=False,
        training_admission=False, cuda_initialized=torch.cuda.is_initialized())
    (N / 'reports/TRAJECTORY_REPLAY_R7_R2.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)
    assert not failures, 'See retained private failure report'


if __name__ == '__main__':
    main()
