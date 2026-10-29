"""CPU lease/ownership tests and installed Ray API inspection; does not start Ray."""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest

N = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(N/'src'))
from gpu_launch_gate_r6 import file_sha

suite = unittest.defaultTestLoader.discover(str(N/'tests'), pattern='test_gpu_private_ray_r6.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
import ray
assert not ray.is_initialized()
init_source = inspect.getsource(ray.init)
shutdown_source = inspect.getsource(ray.shutdown)
assert '_temp_dir' in init_source and 'address_env_var' in init_source
assert 'kill_all_processes' in shutdown_source
ast.parse((N/'src/gpu_probe_r6.py').read_text())
freeze = json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA']
for p, h in freeze.items():
    assert file_sha(N/p) == h, p
old = json.loads((N/'PROVENANCE.json').read_text())['source_files_SHA256']
F = N.parent/'icps_v11_full97_sao_20261024_r2'
for p, h in old.items():
    assert file_sha(F/p.replace('\\', '/')) == h, p
files = ['src/gpu_private_ray_r6.py', 'src/gpu_probe_r6.py', 'tests/test_gpu_private_ray_r6.py',
         'validation/gpu_private_ray_r6_contracts.py', 'ops/gpu_private_ray_r6_contracts.sh']
report = dict(status='PRIVATE_RAY_LEASE_CPU_CONTRACTS_PASS_REAL_RAY_PENDING', tests=result.testsRun,
    prior_attempt="logs/gpu_private_ray_r6_contracts exit1: unrelated older proc environ permission; preserved",
    process_start_cutoff_tested=True, newer_unreadable_process_fails_closed=True, Linux_flock_tested=True, private_marker_tested=True, actual_owned_CPU_child_tested=True,
    child_exited_by_stdin_EOF=True, process_signals_sent=0, global_cleanup=False,
    Ray_initialized=False, GPU_launched=False, live_approval_created=False, training_admitted=False,
    frozen_sources_exact=len(freeze), old_sources_exact=len(old),
    installed_ray=dict(version=ray.__version__, source_path=inspect.getfile(ray.init),
        init_source_SHA=hashlib.sha256(init_source.encode()).hexdigest(),
        shutdown_source_SHA=hashlib.sha256(shutdown_source.encode()).hexdigest()),
    source_SHA={p: file_sha(N/p) for p in files},
    limitations=['No actual Ray startup/shutdown was exercised; only installed API source was inspected.',
      'The CPU child is an owned Python stdin reader, not a Ray worker.',
      'Shared flock coordinates cooperating native launchers; it cannot prevent unrelated programs from taking GPUs or ports.',
      'Resource gate executes under this lock immediately before Ray; private local Ray startup failures remain failures.',
      'No reviewed producer, complete native/offline manifests or current private-Ray config parity receipt exists.',
      'The probe now requires explicit address=local/namespace/private_temp/num_gpus8/dashboardfalse; old config alone will fail closed.',
      'Private directories/logs are retained; no global kill or filesystem cleanup is implemented.'])
with (N/'reports/GPU_PRIVATE_RAY_R6_CONTRACTS.json').open('x') as out:
    json.dump(report, out, indent=2, allow_nan=False)
print(json.dumps(dict(tests=result.testsRun, Ray_initialized=False, GPU=False)))
