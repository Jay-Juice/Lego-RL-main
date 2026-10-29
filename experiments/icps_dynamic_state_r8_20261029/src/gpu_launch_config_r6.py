"""Prepare only a private Ray probe config; never create a launch approval.

Compose current native Hydra trees with the archived, independently compared
commands. Require exact agreement with the frozen resolved reference before
changing only the output namespaces and explicit local Ray initialization.
"""
import copy
import json
from pathlib import Path
import re

from gpu_launch_gate_r6 import B, N, R, canonical_sha, file_sha, require

REFERENCE_SHA = '42d0c0e14303b644e74eef1603da798be63f71c56c928a9739b2fa6b44928208'
OUTPUT_KEYS = {'trainer.default_local_dir', 'trainer.episode_log_dir'}
RAY_KEYS = {'ray_kwargs.ray_init.'+k for k in
            ('address', 'namespace', '_temp_dir', 'num_gpus', 'include_dashboard')}
HISTORICAL_KEYS = {'trainer.experiment_name', 'trainer.default_local_dir',
    'trainer.episode_log_dir', 'trainer.resume_mode',
    'actor_rollout_ref.rollout.trace.experiment_name',
    'actor_rollout_ref.rollout.agent.agent_loop_config_path'}


def flat(value, prefix=''):
    if not isinstance(value, dict) or not value:
        return {prefix: value}
    result = {}
    for key, child in value.items():
        result.update(flat(child, prefix+'.'+key if prefix else key))
    return result


def differences(actual, expected):
    a, b = flat(actual), flat(expected)
    return [dict(key=k, actual=a.get(k), expected=b.get(k),
                 actual_present=k in a, expected_present=k in b)
            for k in sorted(a.keys() | b.keys())
            if k not in a or k not in b or type(a[k]) is not type(b[k]) or a[k] != b[k]]


def run_paths(run):
    run = Path(run)
    require(run.parent == N/'runs' and re.fullmatch(r'gpu-r6-[0-9a-f]{16}', run.name),
            'private config run name/parent')
    require(run.resolve() == run, 'private config run symlink')
    return run, Path('/tmp')/('r6g-'+run.name.removeprefix('gpu-r6-'))


def bind_private_config(seed, run):
    run, tmp = run_paths(run)
    value = copy.deepcopy(seed)
    value['trainer']['default_local_dir'] = str(run/'NEVER_SAVE_CHECKPOINT')
    value['trainer']['episode_log_dir'] = str(run/'episode_logs')
    value['ray_kwargs']['ray_init'].update(address='local', namespace=run.name,
        _temp_dir=str(tmp/'ray'), num_gpus=8, include_dashboard=False)
    return value


def validate_private_config(value, seed, run):
    expected = bind_private_config(seed, run)
    require(not differences(value, expected), 'private config differs from exact approved transformation')
    changed = differences(value, seed)
    require({x['key'] for x in changed} == OUTPUT_KEYS | RAY_KEYS,
            'unexpected private config change set')
    return changed


def compose_command(command, config_dir):
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf
    require(command[1] == '-m' and command[2] in ('gpu_probe_r6', 'verl.trainer.main_ppo'),
            'unknown reference command')
    overrides = [x for x in command[3:] if '=' in x and not x.startswith('--')]
    with initialize_config_dir(config_dir=str(config_dir), version_base=None):
        config = compose(config_name='lego_rl_sync.yaml', overrides=overrides)
    return OmegaConf.to_container(config, resolve=True)


def prepare(run):
    """Read-only, CPU-only preparation. No run directory or receipt is created."""
    ref_path = N/'reports/GPU_PROBE_R6_HYDRA_PARITY.json'
    require(file_sha(ref_path) == REFERENCE_SHA, 'Hydra reference changed')
    ref = json.loads(ref_path.read_text())
    require(ref['passed'] is True and ref['unexpected_differences'] == [] and
            ref['phase21_97']['unexpected'] == [], 'reference parity failed')
    seed = compose_command(ref['formal_command'], R/'src/verl_patch/config')
    baseline = compose_command(ref['baseline_command'], B/'src/verl_patch/config')
    require(not differences(seed, ref['complete_actual_config']), 'current inherited Hydra tree drift')
    require(not differences(baseline, ref['complete_baseline_config']), 'current SAO Hydra tree drift')
    value = bind_private_config(seed, run)
    changed = validate_private_config(value, seed, run)
    phase2 = copy.deepcopy(value)
    phase2['actor_rollout_ref']['actor']['ppo_max_token_len_per_gpu'] = 16384
    phase2['critic']['ppo_max_token_len_per_gpu'] = 45056
    phase2['critic']['forward_max_token_len_per_gpu'] = 45056
    resumed = compose_command(ref['phase21_97']['historical_command'], B/'src/verl_patch/config')
    first_diff, later_diff = differences(value, baseline), differences(phase2, resumed)
    for rows in (first_diff, later_diff):
        require(all(x['key'] in HISTORICAL_KEYS | RAY_KEYS for x in rows),
                'non-namespace/non-resume historical recipe difference')
    paths = [Path(c['actor_rollout_ref']['rollout']['agent']['agent_loop_config_path'])
             for c in (value, baseline, resumed)]
    require(len({file_sha(p) for p in paths}) == 1, 'agent YAML bytes differ')
    from omegaconf import OmegaConf
    require(OmegaConf.to_container(OmegaConf.create(value), resolve=True) == value,
            'prepared config roundtrip changed values')
    return value, dict(status='PRIVATE_CONFIG_PARITY_PASS_NOT_LAUNCH_APPROVAL',
        reference_SHA=REFERENCE_SHA, config_SHA=canonical_sha(value),
        phase2_config_SHA=canonical_sha(phase2), private_changes=changed,
        phase1_historical_differences=first_diff, phase2_historical_differences=later_diff,
        agent_YAML_SHA=file_sha(paths[0]), training_admission=False,
        production_receipt_created=False, Ray_initialized=False, GPU_launched=False,
        limitations=['Config preparation only; shell environment and dependency/asset manifest review remain separate.',
          'Phase2 is a config comparison witness; actual probe uses native per-batch packing overrides.',
          'No Ray, model or optimizer execution; no source review or resource approval inferred.'])
