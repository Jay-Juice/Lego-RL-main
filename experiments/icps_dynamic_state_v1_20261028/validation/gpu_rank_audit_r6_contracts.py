"""CPU assertions, real native subclass API inspection and expanded source inventory."""
import json
from pathlib import Path
import sys
import unittest

N = Path(__file__).resolve().parents[1]
B = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
R = B/'experiments/pi_repair_state_v2_20261015'
F = B/'experiments/icps_v11_full97_sao_20261024_r2'
sys.path.insert(0, str(N/'src'))
from gpu_launch_gate_r6 import file_sha

suite = unittest.defaultTestLoader.discover(str(N/'tests'), pattern='test_gpu_rank_audit_r6.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
import torch
assert not torch.cuda.is_initialized()
freeze = json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA']
for path, expected in freeze.items():
    assert file_sha(N/path) == expected, path
old = json.loads((N/'PROVENANCE.json').read_text())['source_files_SHA256']
for path, expected in old.items():
    assert file_sha(F/path.replace('\\', '/')) == expected, path
native = [
    'src/verl_patch/models/qwen3_5_token_classification.py',
    'third_party/verl/verl/trainer/main_ppo.py',
    'third_party/verl/verl/trainer/ppo/core_algos.py',
    'third_party/verl/verl/trainer/ppo/reward.py',
    'third_party/verl/verl/trainer/ppo/trajectory_filter.py',
    'third_party/verl/verl/workers/engine_workers.py',
    'third_party/verl/verl/workers/engine/utils.py',
    'third_party/verl/verl/workers/engine/veomni/transformer_impl.py',
    'third_party/verl/verl/workers/utils/losses.py',
    'third_party/verl/verl/workers/reward_manager/naive.py',
    'third_party/verl/verl/workers/config/critic.py',
    'third_party/verl/verl/workers/config/actor.py',
    'third_party/verl/verl/single_controller/base/decorator.py',
]
inventory = [dict(path=p, SAO_SHA=file_sha(B/p), inherited_SHA=file_sha(R/p),
                  equal=file_sha(B/p) == file_sha(R/p)) for p in native]
inherited = ['runtime/ray_trainer.py', 'runtime/engine_utils.py', 'src/formal_packing.py',
             'src/formal_storage.py', 'src/formal_checkpoint.py']
for path in inherited:
    assert file_sha(N/path) == file_sha(F/path), path
files = ['src/gpu_rank_audit_r6.py', 'src/gpu_probe_workers_r6.py', 'src/gpu_probe_r6.py',
         'tests/test_gpu_rank_audit_r6.py', 'validation/gpu_rank_audit_r6_contracts.py',
         'ops/gpu_rank_audit_r6_contracts.sh']
report = dict(status='CPU_RANK_AUDIT_CONTRACTS_PASS_ACTUAL_EIGHT_RANKS_PENDING', tests=result.testsRun,
    CPU_tiny_modules=True, synthetic_rank_rows=True, native_worker_subclasses_imported=True,
    native_update_init_methods_inherited=True, ONE_TO_ALL_blocking_registration_checked=True,
    real_distributed_workers_started=False, CUDA_initialized=False, GPU_launched=False,
    optimizer_steps=0, actual_rank_audit_pass=False, training_admitted=False,
    native_source_inventory=inventory, selected_native_files=len(inventory),
    selected_native_source_parity_pass=all(row['equal'] for row in inventory),
    complete_source_review=False, inherited_files_exact=inherited,
    frozen_generator_exact=len(freeze), old_source_exact=len(old),
    source_SHA={p: file_sha(N/p) for p in files},
    limitations=['Synthetic rows test missing/duplicate rank rejection, not real eight-rank execution.',
      'Tiny CPU modules test freeze/head/optimizer assertions, not native Qwen parameter acceptance.',
      'Native class registration/inherited-method identity inspected without constructing a worker.',
      'Thirteen selected files cover worker/loss/reward/filter interfaces; transitive dependency review remains pending.',
      'Native head source is recorded per rank for subsequent review; no whole-source acceptance inferred.',
      'No launch producer/private Ray lifecycle and no GPU launch in this stage.'])
with (N/'reports/GPU_RANK_AUDIT_R6_CONTRACTS.json').open('x') as handle:
    json.dump(report, handle, indent=2, allow_nan=False)
print(json.dumps(dict(tests=result.testsRun, selected_native_equal=report['selected_native_source_parity_pass'], GPU=False)))
