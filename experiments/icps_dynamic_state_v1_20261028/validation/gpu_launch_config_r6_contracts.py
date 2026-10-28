"""Recompose both historical phases and the current private Ray config on CPU."""
import json
import os
from pathlib import Path
import sys
import unittest

N = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(N/'src'))
from gpu_launch_config_r6 import prepare, R
from gpu_launch_gate_r6 import file_sha, canonical_sha
from gpu_private_ray_r6 import validate_ray_namespace

suite = unittest.defaultTestLoader.discover(str(N/'tests'), pattern='test_gpu_launch_config_r6.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
run = N/'runs/gpu-r6-1122334455667788'
assert not run.exists(), 'CPU fixture must not reuse or create a run'
assert os.environ.get('RAY_ADDRESS') in (None, '', 'local')
config, report = prepare(run)
validate_ray_namespace(config, run)
assert not run.exists()
# Native Hydra config search plugins may import Ray/Torch without starting them.
ray_module = sys.modules.get('ray')
torch_module = sys.modules.get('torch')
assert ray_module is None or not ray_module.is_initialized(), 'Ray unexpectedly initialized'
assert torch_module is None or not torch_module.cuda.is_initialized(), 'CUDA unexpectedly initialized'
freeze = json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA']
for p, h in freeze.items():
    assert file_sha(N/p) == h, p
old = json.loads((N/'PROVENANCE.json').read_text())['source_files_SHA256']
F = N.parent/'icps_v11_full97_sao_20261024_r2'
for p, h in old.items():
    assert file_sha(F/p.replace('\\', '/')) == h, p
trees = {}
for root in (R/'src/verl_patch/config', R/'third_party/verl/verl/trainer/config',
             N.parents[1]/'src/verl_patch/config', N.parents[1]/'third_party/verl/verl/trainer/config'):
    assert root.is_dir(), root
    for p in sorted(root.rglob('*.yaml')):
        trees[str(p)] = file_sha(p)
report.update(tests=result.testsRun,
    prior_attempt='logs/gpu_private_config_r6_contracts exit1: overstrict no-Ray-import assertion after native Hydra composition; retained',
    Ray_imported=ray_module is not None, CUDA_initialized=False, current_config_trees_SHA=canonical_sha(trees),
    current_config_files=trees, frozen_sources_exact=len(freeze), old_sources_exact=len(old),
    run_directory_created=False, full_horizon_preserved=97,
    source_SHA={p:file_sha(N/p) for p in ['src/gpu_launch_config_r6.py',
        'tests/test_gpu_launch_config_r6.py', 'validation/gpu_launch_config_r6_contracts.py',
        'ops/gpu_launch_config_r6_contracts.sh']})
with (N/'reports/GPU_PRIVATE_CONFIG_R6_CONTRACTS.json').open('x') as out:
    json.dump(report, out, indent=2, allow_nan=False)
print(json.dumps({k:report[k] for k in ['status', 'tests', 'config_SHA', 'production_receipt_created']}))
