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
    from dynamic_session_r8 import R8DynamicSession as R6DynamicSessionR2
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
        snapshot = dict(files={'fixture.py': f'LIMIT = {constant}\n\n@cache_{constant}\ndef compute_total(x):\n    return x+{constant}\n\ndef extra(x):\n    return x+{constant+1}\n'},
                        stable=True, limited=False)
        record = session.capture(snapshot, task_uid='r6-gpu-fixture', session_id='r6-gpu',
                                 logical_call_id=f'call-{seq}', seq=seq)
        assert record['pi_format'] == 'icps_dynamic_v1' and record['pi_ids']
        assert record['windows'] and any('return' in w['code'] for w in record['windows']), 'fixture must contain actual source, not only unknown markers'
        assert len(record['pi_ids']) <= (1024 if seq == 1 else 128)
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


def optional_mfu_controllers(trainer):
    """Probe-instance-only telemetry compatibility; native worker math is untouched.

    This installed engine omits optional MFU telemetry. Retain the complete
    inspected controller methods, changing only their three MFU reads/pops.
    Missing MFU is absent/None, never a fabricated numeric measurement.
    """
    import inspect, textwrap, types
    edits = {
        '_compute_old_log_prob': ('old_log_prob_mfu = tu.get(output, "metrics")["mfu"]',
                                 'old_log_prob_mfu = tu.get(output, "metrics").get("mfu")'),
        '_update_actor': ('actor_output["perf/mfu/actor"] = actor_output.pop("actor/mfu")',
                         'if "actor/mfu" in actor_output: actor_output["perf/mfu/actor"] = actor_output.pop("actor/mfu")'),
        '_update_critic': ('output["perf/mfu/critic"] = output.pop("critic/mfu")',
                          'if "critic/mfu" in output: output["perf/mfu/critic"] = output.pop("critic/mfu")'),
    }
    witness = {}
    for name, (before, after) in edits.items():
        original = getattr(type(trainer), name)
        source = textwrap.dedent(inspect.getsource(original))
        assert source.count(before) == 1, (name, 'native controller changed')
        patched = source.replace(before, after)
        namespace = dict(original.__globals__)
        exec(compile(patched, '<R6-probe-optional-MFU:'+name+'>', 'exec'), namespace)
        setattr(trainer, name, types.MethodType(namespace[name], trainer))
        witness[name] = dict(original_source_SHA=hashlib.sha256(source.encode()).hexdigest(),
                             replacement_before=before, replacement_after=after)
    return witness


class ProbeRunner(TaskRunner):
    def add_actor_rollout_worker(self, config):
        from verl.trainer.ppo.ray_trainer import Role
        from gpu_probe_workers_r6 import AuditedActorWorker
        _, group_class = super().add_actor_rollout_worker(config)
        roles = [role for role in (Role.ActorRollout, Role.ActorRolloutRef) if role in self.role_worker_mapping]
        assert len(roles) == 1
        self.role_worker_mapping[roles[0]] = ray.remote(AuditedActorWorker)
        return AuditedActorWorker, group_class

    def add_critic_worker(self, config):
        from verl.trainer.ppo.ray_trainer import Role
        from gpu_probe_workers_r6 import AuditedCriticWorker
        super().add_critic_worker(config)
        self.role_worker_mapping[Role.Critic] = ray.remote(AuditedCriticWorker)

    def run(self, config):
        original_fit = RayPPOTrainer.fit

        def probe(trainer):
            from gpu_rank_audit_r6 import validate_rank_rows, compare_stages
            def audit(stage):
                return dict(actor=validate_rank_rows(trainer.actor_rollout_wg.r6_rank_audit(stage), 'actor', stage),
                            critic=validate_rank_rows(trainer.critic_wg.r6_rank_audit(stage), 'critic', stage))
            telemetry_compatibility = optional_mfu_controllers(trainer)
            tokenizer = trainer.tokenizer
            contracts = cpu_contracts(tokenizer)
            assert trainer.total_training_steps == 97 and len(trainer.train_dataloader) == 97
            trainer.checkpoint_manager.sleep_replicas()
            rank_before = audit('before_updates')
            with (Path(os.environ['ICPS_FORMAL_RUN_DIR'])/'rank_before.json').open('x') as handle:
                json.dump(rank_before, handle, indent=2, allow_nan=False)
            trainer.global_steps = 20
            print('R8_GPU baseline_values', flush=True)
            baseline = trainer._compute_values(short_batch(tokenizer, 'baseline')[0]).batch['values']
            empty = trainer._compute_values(short_batch(tokenizer, 'empty')[0]).batch['values']
            assert torch.isfinite(baseline).all() and torch.isfinite(empty).all()
            torch.testing.assert_close(baseline, empty, atol=1e-5, rtol=1e-5)
            phases = []
            for step in (20, 21):
                trainer.global_steps = step  # packing API only, not real training progress
                batch, witness = short_batch(tokenizer)
                # Use native current-policy probabilities for a well-scaled disposable
                # policy update. Synthetic zero rollout probabilities would distort IS.
                old, _ = trainer._compute_old_log_prob(batch)
                without_pi = short_batch(tokenizer, 'baseline')[0]
                old_off, _ = trainer._compute_old_log_prob(without_pi)
                torch.testing.assert_close(old.batch['old_log_probs'], old_off.batch['old_log_probs'], atol=1e-5, rtol=1e-5)
                batch.batch['old_log_probs'] = old.batch['old_log_probs'].clone()
                batch.batch['rollout_log_probs'] = old.batch['old_log_probs'].clone()
                original = {k: v.clone() for k, v in batch.batch.items()}
                print(f'R8_GPU phase{step} values', flush=True)
                values = trainer._compute_values(batch)
                assert torch.isfinite(values.batch['values']).all()
                batch = batch.union(values)
                print(f'R8_GPU phase{step} critic_update', flush=True)
                critic = trainer._update_critic(batch)
                print(f'R8_GPU phase{step} actor_update', flush=True)
                # Observe the actual controller-to-worker Actor boundary; forward
                # unchanged to the native method after verifying PI was removed.
                from verl.trainer.ppo import ray_trainer as rt
                expected = batch.to_tensordict()
                expected.pop('pi_call_records', None)
                expected = rt.left_right_2_no_padding(expected)
                native_actor_update = trainer.actor_rollout_wg.update_actor
                actor_boundary = []
                def checked_actor_update(td):
                    assert not any(str(k).startswith(('pi_', 'critic_')) for k in td.keys())
                    for key in original:
                        if key not in expected: continue
                        a,b=td[key],expected[key]
                        if getattr(a,'is_nested',False):
                            assert torch.equal(a.values(),b.values()) and torch.equal(a.offsets(),b.offsets()), key
                        else: assert torch.equal(a,b), key
                    actor_boundary.append(True)
                    return native_actor_update(td)
                trainer.actor_rollout_wg.update_actor = checked_actor_update
                try:
                    actor = trainer._update_actor(batch)
                finally:
                    trainer.actor_rollout_wg.update_actor = native_actor_update
                assert actor_boundary == [True]
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
                                   values_shape=list(values.batch['values'].shape),
                                   values_min=float(values.batch['values'].min()),
                                   values_max=float(values.batch['values'].max()),
                                   values_mean=float(values.batch['values'].mean()),
                                   Actor_boundary_PI_absent=True, Actor_boundary_tensors_exact=True,
                                   Actor_PI_on_off_logprob_max_abs_diff=float((old.batch['old_log_probs']-old_off.batch['old_log_probs']).abs().max())))
                with (Path(os.environ['ICPS_FORMAL_RUN_DIR'])/f'phase_{step}.json').open('x') as f:
                    json.dump(phases[-1],f,indent=2,allow_nan=False)
            rank_after = audit('after_updates')
            compare_stages(rank_before, rank_after)
            with (Path(os.environ['ICPS_FORMAL_RUN_DIR'])/'rank_after.json').open('x') as handle:
                json.dump(rank_after, handle, indent=2, allow_nan=False)
            out = Path(os.environ['ICPS_FORMAL_RUN_DIR'])/'result.json'
            with out.open('x') as f:
                json.dump(dict(status='native_updates_and_rank_checks_complete_pending_review', contracts=contracts,
                    rank_before=rank_before, rank_after=rank_after,
                    probe_controller_optional_MFU=telemetry_compatibility,
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
    assert os.environ.get('ICPS_R8_GPU_APPROVED_LAUNCH') == '1', 'separate resource/source gate required'
    assert os.environ.get('ICPS_V11_OVERLAY_ACTIVE') == '1'
    assert config.trainer.resume_mode == 'disable'
    assert config.trainer.experiment_name == 'sao-qwen35-9b-b64-dynamic-r6-gpu-probe-20261028'
    assert not Path(config.trainer.default_local_dir).exists(), 'no checkpoint reuse'
    run = Path(os.environ['ICPS_FORMAL_RUN_DIR'])
    from gpu_launch_gate_r6 import consume
    from gpu_private_ray_r6 import PrivateRayLease, validate_ray_namespace
    resolved = OmegaConf.to_container(config, resolve=True)
    assert not ray.is_initialized(), 'probe must own its local Ray instance'
    validate_ray_namespace(resolved, run)
    with PrivateRayLease(run) as lease:
        import tempfile, time
        short_tmp = lease.temp/'tmp'
        short_tmp.mkdir(mode=0o700)
        os.environ['TMPDIR'] = str(short_tmp)
        tempfile.tempdir = None  # Native imports may have cached the previous long path.
        consume(resolved)  # Fresh resource observation while holding native shared launch lock.
        with (run/'resolved_actual.json').open('x') as f:
            json.dump(resolved, f, indent=2)
        try:
            run_ppo(config, task_runner_class=ray.remote(num_cpus=1)(ProbeRunner))
        finally:
            ray.shutdown()  # address=local: terminates only the Ray instance created here.
            from gpu_private_ray_r6 import owned_processes
            deadline = time.monotonic()+20
            while True:
                try:
                    remaining = owned_processes(lease.owner)
                except PermissionError:
                    # /proc can become unreadable while a worker exits. Retry,
                    # never count an unreadable process as gone or passed.
                    if time.monotonic() >= deadline: raise
                    time.sleep(0.5)
                    continue
                if not remaining or time.monotonic() >= deadline: break
                time.sleep(0.5)  # No signals or global cleanup; lease checks final state.


if __name__ == '__main__':
    main()
