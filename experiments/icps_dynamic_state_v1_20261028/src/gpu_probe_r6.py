"""Disposable native-engine probe; real frozen R6 PI, synthetic Actor batch.

Never a training entry: no rollout/verifier, no checkpoint, no reusable weights.
Invocation requires a separately reviewed launch/resource receipt.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path

import hydra
import numpy as np
import ray
import torch
from omegaconf import OmegaConf
from verl import DataProto
from verl.trainer.main_ppo import TaskRunner, run_ppo
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from verl.utils.metric import reduce_metrics


def short_batch(tokenizer, mode='real'):
    from dynamic_session_r6_r2 import R6DynamicSessionR2
    from verl_patch.agent_loop.privileged_critic_builder import interleave
    assert mode in ('real', 'empty', 'baseline')
    enc = lambda text: tokenizer.encode(text, add_special_tokens=False)
    prompt = enc('Inspect the current Python workspace.\n')
    first = enc('Inspect function compute_total.\n')
    observation = enc('Workspace edit completed.\n')
    second = enc('Review the modified function.\n')
    response = first + observation + second
    plen, rlen = len(prompt), len(response)
    mask = [1]*len(first) + [0]*len(observation) + [1]*len(second)
    session = R6DynamicSessionR2('function compute_total in fixture.py returns an incorrect integer', tokenizer, 'r6-gpu-fixture', 'r6-gpu')
    records = []
    for seq, (constant, start, end) in enumerate([
            (1, plen, plen+len(first)),
            (2, plen+len(first)+len(observation), plen+rlen)], 1):
        snapshot = dict(files={'fixture.py': f'def compute_total(x):\n    return x+{constant}\n'},
                        stable=True, limited=False)
        record = session.capture(snapshot, task_uid='r6-gpu-fixture', session_id='r6-gpu',
                                 logical_call_id=f'call-{seq}', seq=seq)
        assert record['pi_format'] == 'icps_dynamic_v1' and record['pi_ids']
        assert record['windows'] and any('return' in w['code'] for w in record['windows']), 'fixture must contain actual source, not only unknown markers'
        assert len(record['pi_ids']) <= (192 if seq == 1 else 128)
        record.update(actor_response_start_abs=start, actor_response_end_abs=end)
        if mode == 'empty':
            record['pi_ids'] = []
        records.append(record)
    ids = torch.tensor([prompt+response]*64, dtype=torch.long)
    data = dict(input_ids=ids, attention_mask=torch.ones_like(ids),
                position_ids=torch.arange(ids.shape[1])[None].repeat(64, 1),
                prompts=ids[:, :plen].clone(), responses=ids[:, plen:].clone(),
                response_mask=torch.tensor([mask]*64), old_log_probs=torch.zeros(64, rlen),
                rollout_log_probs=torch.zeros(64, rlen),
                returns=torch.tensor([mask]*64, dtype=torch.float32),
                advantages=torch.tensor([mask]*64, dtype=torch.float32)*0.1)
    non_tensor = {}
    if mode != 'baseline':
        rows = np.empty(64, dtype=object)
        for i in range(64):
            rows[i] = copy.deepcopy(records)
        non_tensor['pi_call_records'] = rows
        critic, gather, pi_mask = interleave(prompt+response, plen, mask, records,
                                            total_pi_budget=4096, tokenizer=tokenizer)
        assert [token for token, pi in zip(critic, pi_mask) if not pi] == prompt+response
        for i, pos in enumerate(gather):
            assert critic[pos+1] == response[i]
        prefix, prefix_gather, _ = interleave((prompt+response)[:records[0]['actor_response_end_abs']],
            plen, mask[:len(first)], records[:1], total_pi_budget=4096, tokenizer=tokenizer)
        assert prefix == critic[:len(prefix)] and prefix_gather == gather[:len(prefix_gather)]
    witness = dict(rows=64, actor_tokens=plen+rlen, response_tokens=rlen,
                   PI_tokens=[len(r['pi_ids']) for r in records], mode=mode,
                   source_windows=[len(r['windows']) for r in records],
                   PI_ID_SHA=hashlib.sha256(json.dumps([r['pi_ids'] for r in records]).encode()).hexdigest())
    return DataProto.from_dict(data, non_tensor, meta_info={'temperature': 1.0}), witness


def cpu_contracts(tokenizer):
    real, witness = short_batch(tokenizer)
    for mode in ('baseline', 'empty'):
        other, _ = short_batch(tokenizer, mode)
        for key in real.batch.keys():
            assert torch.equal(real.batch[key], other.batch[key]), (mode, key)
    assert len({id(row) for row in real.non_tensor_batch['pi_call_records']}) == 64
    return dict(passed=True, real_Qwen=True, GPU=False, independent_rows=True,
                Actor_tensors_equal=True, pretoken_gather_and_causal_prefix=True, fixture=witness)


class ProbeRunner(TaskRunner):
    def run(self, config):
        original_fit = RayPPOTrainer.fit

        def probe(trainer):
            tokenizer = trainer.tokenizer
            contracts = cpu_contracts(tokenizer)
            assert trainer.total_training_steps == 97 and len(trainer.train_dataloader) == 97
            trainer.checkpoint_manager.sleep_replicas()
            trainer.global_steps = 20
            print('R6_GPU baseline_values', flush=True)
            baseline = trainer._compute_values(short_batch(tokenizer, 'baseline')[0]).batch['values']
            empty = trainer._compute_values(short_batch(tokenizer, 'empty')[0]).batch['values']
            assert torch.isfinite(baseline).all() and torch.isfinite(empty).all()
            torch.testing.assert_close(baseline, empty, atol=1e-5, rtol=1e-5)
            phases = []
            for step in (20, 21):
                trainer.global_steps = step  # packing API only, not real training progress
                batch, witness = short_batch(tokenizer)
                original = {k: v.clone() for k, v in batch.batch.items()}
                print(f'R6_GPU phase{step} values', flush=True)
                values = trainer._compute_values(batch)
                assert torch.isfinite(values.batch['values']).all()
                batch = batch.union(values)
                print(f'R6_GPU phase{step} critic_update', flush=True)
                critic = trainer._update_critic(batch)
                print(f'R6_GPU phase{step} actor_update', flush=True)
                actor = trainer._update_actor(batch)
                for key, value in original.items():
                    assert torch.equal(batch.batch[key], value), key
                metrics = {**reduce_metrics(critic.meta_info['metrics']),
                           **reduce_metrics(actor.meta_info['metrics'])}
                metrics = {k: float(v) for k, v in metrics.items()}
                assert metrics and all(math.isfinite(v) for v in metrics.values())
                for role in ('critic', 'actor'):
                    grad = {k: v for k, v in metrics.items() if k.startswith(role+'/') and 'grad_norm' in k}
                    assert grad and any(v > 0 for v in grad.values()), (role, metrics)
                phases.append(dict(packing_step=step, metrics=metrics, fixture=witness,
                                   values_shape=list(values.batch['values'].shape)))
            out = Path(os.environ['ICPS_FORMAL_RUN_DIR'])/'result.json'
            with out.open('x') as f:
                json.dump(dict(status='native_updates_complete_pending_rank_audit', contracts=contracts,
                    phases=phases, empty_PI_value_max_abs_diff=float((baseline-empty).abs().max()),
                    synthetic_fixture=True, actual_Actor_rollout=False, checkpoint_saved=False,
                    reuse_weights_allowed=False, training_admission=False), f, indent=2, allow_nan=False)
            trainer._shutdown_dump_executor()
        # Probe-process-only fit replacement; selector/runtime sources untouched.
        RayPPOTrainer.fit = probe
        try:
            return super().run(config)
        finally:
            RayPPOTrainer.fit = original_fit


@hydra.main(config_path=None, config_name='lego_rl_sync', version_base=None)
def main(config):
    # A launch receipt is intentionally not created by this module or CPU preparation.
    assert os.environ.get('ICPS_R6_GPU_APPROVED_LAUNCH') == '1', 'separate resource/source gate required'
    assert os.environ.get('ICPS_V11_OVERLAY_ACTIVE') == '1'
    assert config.trainer.resume_mode == 'disable'
    assert config.trainer.experiment_name == 'sao-qwen35-9b-b64-dynamic-r6-gpu-probe-20261028'
    assert not Path(config.trainer.default_local_dir).exists(), 'no checkpoint reuse'
    run = Path(os.environ['ICPS_FORMAL_RUN_DIR'])
    from gpu_launch_gate_r6 import consume
    consume(OmegaConf.to_container(config, resolve=True))
    with (run/'resolved_actual.json').open('x') as f:
        json.dump(OmegaConf.to_container(config, resolve=True), f, indent=2)
    try:
        run_ppo(config, task_runner_class=ray.remote(num_cpus=1)(ProbeRunner))
    finally:
        ray.shutdown()


if __name__ == '__main__':
    main()
