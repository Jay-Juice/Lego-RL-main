"""Isolated real-engine acceptance; synthetic updates never enter production."""
import hashlib
import json
import math
import os
from pathlib import Path

import hydra
import numpy as np
import ray
import torch
from omegaconf import open_dict
from verl.trainer.main_ppo import TaskRunner, run_ppo
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from verl.utils.metric import reduce_metrics
from verl_patch.pi_gpu_smoke import short_batch
from harbor_patch.privileged_state.repair_state import build_snapshot, serialize


def fixture(tokenizer):
    batch = short_batch(tokenizer)
    records = batch.non_tensor_batch['pi_call_records'][0]
    session, output = {}, []
    for index, record in enumerate(records):
        source = f'def f(x):\n    return x + {index + 2}\n'
        snap = build_snapshot({'baseline_sha': 'synthetic-prepared', 'files': [{
            'path': 'example.py', 'kind': 'text', 'status': 'modified',
            'old_source': 'def f(x):\n    return x + 1\n', 'current_source': source,
            'sha256': hashlib.sha256(source.encode()).hexdigest()}]})
        pi = serialize(snap, tokenizer, session, [], logical_call_id=index, output_limit=32768)
        output.append({**record, **pi, 'state_hash': snap['state_hash']})
    array = np.empty(64, dtype=object)
    array[:] = [output for _ in range(64)]
    batch.non_tensor_batch['pi_call_records'] = array
    return batch


def batch_digest(value):
    digest = hashlib.sha256()
    def visit(v):
        if isinstance(v, dict):
            for k in sorted(v): digest.update(str(k).encode()); visit(v[k])
        elif isinstance(v, torch.Tensor):
            digest.update(str((v.dtype, v.shape)).encode())
            digest.update(v.contiguous().cpu().view(torch.uint8).numpy().tobytes())
        elif isinstance(v, np.ndarray):
            visit(v.tolist())
        elif isinstance(v, (list, tuple)):
            for x in v: visit(x)
        else: digest.update(repr(v).encode())
    visit(value)
    return digest.hexdigest()


def metrics(result):
    out = {k: float(v) for k, v in reduce_metrics(result.meta_info['metrics']).items()}
    assert all(math.isfinite(v) for v in out.values()), out
    return out


class AcceptanceRunner(TaskRunner):
    def run(self, config):
        original = RayPPOTrainer.fit
        def acceptance(trainer):
            def stage(name): print('PI_V2_ACCEPTANCE_STAGE', name, flush=True)
            trainer.global_steps = 0
            trainer._load_checkpoint()
            tokenizer = trainer.tokenizer
            trainer.checkpoint_manager.sleep_replicas()
            stage('empty_pi_equivalence')
            baseline = trainer._compute_values(short_batch(tokenizer, pi=False)).batch['values']
            empty = trainer._compute_values(short_batch(tokenizer, empty=True)).batch['values']
            torch.testing.assert_close(baseline, empty, atol=1e-5, rtol=1e-5)
            batch = fixture(tokenizer)
            preserved = {k: v.clone() for k,v in batch.batch.items()}
            stage('v2_values_and_warmup_critic_update')
            values = trainer._compute_values(batch)
            assert torch.isfinite(values.batch['values']).all()
            batch = batch.union(values)
            first = metrics(trainer._update_critic(batch))
            # Advance real dataloader without running any task. This is a synthetic
            # checkpoint at step 10, not a claim of ten real training updates.
            iterator = iter(trainer.train_dataloader)
            for _ in range(10): next(iterator)
            trainer.global_steps = 10
            stage('warmup_save_actor_never_updated')
            trainer._save_checkpoint()
            checkpoint = Path(config.trainer.default_local_dir) / 'global_step_10'
            from verl_patch.agent_loop.pi_checkpoint import validate_complete
            manifest = validate_complete(checkpoint, config.trainer.experiment_name)
            expected_next = batch_digest(next(iterator))
            saved_values = trainer._compute_values(batch).batch['values'].clone()
            stage('uninterrupted_next_critic_update')
            uninterrupted = metrics(trainer._update_critic(batch))
            after = trainer._compute_values(batch).batch['values'].clone()
            # Real distributed model/optimizer/scheduler/RNG load after perturbing
            # the Critic and advancing the loader. Keep all checkpoint artifacts.
            with open_dict(config): config.trainer.resume_mode = 'auto'
            stage('restore_warmup_checkpoint')
            trainer._load_checkpoint()
            assert trainer.global_steps == 10
            restored_next = batch_digest(next(iter(trainer.train_dataloader)))
            assert expected_next == restored_next, (expected_next, restored_next)
            restored_values = trainer._compute_values(batch).batch['values']
            torch.testing.assert_close(saved_values, restored_values, atol=1e-5, rtol=1e-5)
            stage('resumed_next_critic_update')
            resumed = metrics(trainer._update_critic(batch))
            resumed_after = trainer._compute_values(batch).batch['values']
            torch.testing.assert_close(after, resumed_after, atol=1e-4, rtol=1e-4)
            for key in uninterrupted:
                if any(s in key for s in ('loss', 'lr', 'grad_norm')):
                    assert math.isclose(uninterrupted[key], resumed[key], rel_tol=1e-4, abs_tol=1e-5), key
            stage('actor_update_after_restore')
            actor = metrics(trainer._update_actor(batch))
            for k,v in preserved.items(): torch.testing.assert_close(batch.batch[k], v, atol=0, rtol=0)
            result = {'status': 'passed', 'model': config.actor_rollout_ref.model.path,
                'sp_size': 8, 'logical_batch': 64, 'synthetic_batch': True,
                'synthetic_checkpoint_step': 10, 'actual_warmup_critic_updates_before_save': 1,
                'actor_updates_before_save': 0, 'checkpoint': str(checkpoint),
                'checkpoint_required_bytes': sum(manifest['files'].values()),
                'empty_pi_max_abs_diff': float((baseline-empty).abs().max()),
                'restore_value_max_abs_diff': float((saved_values-restored_values).abs().max()),
                'next_update_value_max_abs_diff': float((after-resumed_after).abs().max()),
                'next_batch_sha256': expected_next, 'first_critic': first,
                'uninterrupted_critic': uninterrupted, 'resumed_critic': resumed, 'actor': actor,
                'source_revision': os.environ['PI_SOURCE_REVISION'],
                'production_optimizer_updates': 0,
                'limits': 'Short synthetic trajectories; no efficacy claim or maximum-length GPU stress test.'}
            destination = Path(os.environ['PI_ACCEPTANCE_RESULT'])
            with destination.open('x') as handle: json.dump(result, handle, indent=2)
            stage('PASSED')
            trainer._shutdown_dump_executor()
        RayPPOTrainer.fit = acceptance
        try: return super().run(config)
        finally: RayPPOTrainer.fit = original


@hydra.main(config_path='config', config_name='ppo_trainer', version_base=None)
def main(config):
    run_ppo(config, task_runner_class=ray.remote(num_cpus=1)(AcceptanceRunner))


if __name__ == '__main__': main()
