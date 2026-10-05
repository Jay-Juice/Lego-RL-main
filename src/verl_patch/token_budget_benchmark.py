"""Opt-in isolated capture/replay entrypoint; never used by production training.

Capture stops before either optimizer update. Replay reloads checkpoint before
both warmup and measurement, uses the same serialized DataProto, and never saves
weights. Original verl update methods and loss functions are unchanged.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time

import hydra
import ray
import torch
from omegaconf import OmegaConf, open_dict
from verl.trainer.main_ppo import TaskRunner, run_ppo
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from verl.utils.metric import reduce_metrics


class CapturedBatch(Exception):
    pass


def prompt_fingerprint(prompts):
    # Agent-loop inputs can contain only raw chat in non_tensor_batch.
    if prompts.batch is not None and 'input_ids' in prompts.batch:
        value = prompts.batch['input_ids'].cpu().contiguous().numpy().tobytes()
        kind = 'input_ids'
    else:
        raw = prompts.non_tensor_batch['raw_prompt']
        def normalize(item):
            if isinstance(item, dict):
                return {k: normalize(v) for k, v in item.items()}
            if isinstance(item, (list, tuple)):
                return [normalize(v) for v in item]
            if hasattr(item, 'tolist'):
                return normalize(item.tolist())
            return item
        value = json.dumps(normalize(raw), ensure_ascii=False, sort_keys=True).encode('utf-8')
        kind = 'raw_prompt'
    return kind, hashlib.sha256(value).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def describe_batch(batch):
    assert len(batch) == 64, f'Expected fixed batch64, got {len(batch)}'
    required = {'input_ids', 'attention_mask', 'response_mask', 'returns',
                'values', 'advantages', 'old_log_probs'}
    assert required <= set(batch.batch.keys()), required - set(batch.batch.keys())
    for key, value in batch.batch.items():
        if value.is_floating_point():
            assert torch.isfinite(value).all(), f'Nonfinite tensor {key}'
    return {'rows': len(batch),
            'attention_tokens': int(batch.batch['attention_mask'].sum()),
            'response_tokens': int(batch.batch['response_mask'].sum()),
            'shapes': {k: list(v.shape) for k, v in batch.batch.items()}}


class GpuSampler:
    def __init__(self):
        self.stop_event = threading.Event()
        self.peaks = {}
        self.errors = []

    def sample(self):
        while not self.stop_event.is_set():
            try:
                output = subprocess.check_output([
                    'nvidia-smi', '--query-gpu=index,memory.used',
                    '--format=csv,noheader,nounits'], text=True, timeout=5)
                for line in output.splitlines():
                    index, used = [int(x.strip()) for x in line.split(',')]
                    self.peaks[index] = max(self.peaks.get(index, 0), used)
            except Exception as exc:
                self.errors.append(str(exc))
            self.stop_event.wait(1)

    def __enter__(self):
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop_event.set()
        self.thread.join(timeout=7)


def run_replay(trainer, root, role):
    payload = root / 'fixed_batch.pt'
    manifest = json.loads((root / 'capture.json').read_text())
    assert sha256(payload) == manifest['sha256']
    budget = (trainer.config.critic if role == 'critic' else
              trainer.config.actor_rollout_ref.actor).ppo_max_token_len_per_gpu
    target = root / f'{role}_{budget}.json'
    assert not target.exists(), f'Refuse to overwrite result: {target}'
    result = {'role': role, 'budget': budget, 'input': manifest,
              'checkpoint': trainer.config.trainer.resume_from_path, 'runs': []}
    trainer.checkpoint_manager.sleep_replicas()
    # User may request a single practical trial to avoid another full update.
    # Its timing includes first-use overhead; do not call it warmed/controlled.
    phases = ('single_cold_trial',) if os.environ.get('LEGO_TOKEN_BENCH_SINGLE') == '1' else ('warmup', 'measured')
    result['timing_protocol'] = list(phases)
    for phase in phases:
        # Reload restores models, optimizers, scheduler, RNG and data state.
        trainer._load_checkpoint()
        assert trainer.global_steps == 20
        batch = torch.load(payload, map_location='cpu', weights_only=False)
        assert describe_batch(batch) == manifest['batch']
        method = trainer._update_critic if role == 'critic' else trainer._update_actor
        with GpuSampler() as gpu:
            start = time.perf_counter()
            output = method(batch)
            elapsed = time.perf_counter() - start
        metrics = {k: float(v) for k, v in reduce_metrics(output.meta_info['metrics']).items()}
        assert all(math.isfinite(v) for v in metrics.values()), metrics
        result['runs'].append({'phase': phase, 'seconds': elapsed,
                               'metrics': metrics, 'gpu_peak_MiB': gpu.peaks,
                               'gpu_sampler_errors': gpu.errors})
        (root / f'{role}_{budget}.progress.json').write_text(json.dumps(result, indent=2))
        print('TOKEN_BENCH_PHASE', json.dumps(result['runs'][-1]), flush=True)
    target.write_text(json.dumps(result, indent=2))
    trainer._shutdown_dump_executor()


class BenchmarkRunner(TaskRunner):
    def run(self, config):
        mode = os.environ['LEGO_TOKEN_BENCH_MODE']
        assert mode in ('capture', 'critic', 'actor')
        root = Path(os.environ['LEGO_TOKEN_BENCH_ROOT']).resolve()
        repo = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
        assert root.is_relative_to(repo / 'logs')
        checkpoint = repo / 'checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-b64-w32-v6d-20260930/global_step_20'
        assert (checkpoint / 'data.pt').is_file()
        root.mkdir(parents=True, exist_ok=True)
        with open_dict(config):
            config.trainer.resume_mode = 'resume_path'
            config.trainer.resume_from_path = str(checkpoint)
            config.trainer.del_local_ckpt_after_load = False
            config.trainer.save_freq = 0
            config.trainer.default_local_dir = str(root / 'unused_checkpoints')
            config.trainer.test_freq = 0
            config.trainer.val_before_train = False
        (root / f'config_{mode}_{config.critic.ppo_max_token_len_per_gpu}_{config.actor_rollout_ref.actor.ppo_max_token_len_per_gpu}.yaml').write_text(OmegaConf.to_yaml(config, resolve=True))
        original_fit = RayPPOTrainer.fit
        original_critic = RayPPOTrainer._update_critic
        original_save = RayPPOTrainer._save_checkpoint

        def forbidden_save(*args, **kwargs):
            raise RuntimeError('Benchmark must never save model checkpoints')

        def capture(trainer, batch):
            assert trainer.global_steps == 21
            description = describe_batch(batch)
            target = root / 'fixed_batch.pt'
            assert not target.exists(), 'Fixed input already exists; do not regenerate'
            batch.to('cpu')
            torch.save(batch, target)
            (root / 'capture.json').write_text(json.dumps({
                'batch': description, 'sha256': sha256(target),
                'checkpoint': str(checkpoint), 'global_step': 21,
                'optimizer_updates': 0}, indent=2))
            print('TOKEN_BENCH_CAPTURE_COMPLETE', description, flush=True)
            raise CapturedBatch()

        def fit(trainer):
            if mode == 'capture':
                manager = trainer.async_rollout_manager
                original_generate = manager.generate_sequences
                def timed_generate(prompts):
                    start = time.perf_counter()
                    input_kind, input_hash = prompt_fingerprint(prompts)
                    output = original_generate(prompts)
                    record = {'seconds': time.perf_counter() - start,
                              'workers': config.actor_rollout_ref.rollout.agent.num_workers,
                              'input_rows': len(prompts), 'prompt_hash_kind': input_kind,
                              'prompt_sha256': input_hash,
                              'output_rows': len(output),
                              'meta_info': output.meta_info}
                    for key in ('attention_mask', 'response_mask'):
                        if key in output.batch:
                            record[key + '_sum'] = int(output.batch[key].sum().item())
                    (root / 'rollout_timing.json').write_text(json.dumps(record, indent=2, default=str))
                    print('TOKEN_BENCH_ROLLOUT', record['seconds'], flush=True)
                    return output
                manager.generate_sequences = timed_generate
                try:
                    return original_fit(trainer)
                except CapturedBatch:
                    trainer._shutdown_dump_executor()
                    return
                finally:
                    manager.generate_sequences = original_generate
            return run_replay(trainer, root, mode)

        RayPPOTrainer.fit = fit
        RayPPOTrainer._save_checkpoint = forbidden_save
        if mode == 'capture':
            RayPPOTrainer._update_critic = capture
        try:
            return super().run(config)
        finally:
            RayPPOTrainer.fit = original_fit
            RayPPOTrainer._update_critic = original_critic
            RayPPOTrainer._save_checkpoint = original_save


@hydra.main(config_path=None, config_name=None, version_base=None)
def main(config):
    run_ppo(config, task_runner_class=ray.remote(num_cpus=1)(BenchmarkRunner))


if __name__ == '__main__':
    main()
