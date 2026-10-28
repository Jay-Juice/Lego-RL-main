"""CPU gate contracts plus read-only current resource observation. Never grants launch."""
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import gpu_launch_gate_r6 as gate

suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_gpu_launch_gate_r6.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
freeze = json.loads((ROOT/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA']
for name, expected in freeze.items():
    assert gate.file_sha(ROOT/name) == expected, name
resources = gate.collect_resources()
try:
    gate.validate_resources(resources, time.time())
    resource_pass, resource_error = True, None
except gate.GateError as exc:
    resource_pass, resource_error = False, str(exc)
files = ['src/gpu_launch_gate_r6.py', 'src/gpu_probe_r6.py', 'tests/test_gpu_launch_gate_r6.py',
         'validation/gpu_launch_gate_r6_contracts.py', 'ops/gpu_launch_gate_r6_contracts.sh']
report = dict(status='CPU_RECEIPT_CONSUMER_CONTRACTS_PASS_LAUNCHER_PENDING',
    tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    synthetic_receipts_only=True, live_approval_created=False, GPU_launched=False,
    frozen_generator_files_exact=len(freeze), current_resources=resources,
    resource_gate_pass=resource_pass, resource_rejection=resource_error,
    source_SHA={name: gate.file_sha(ROOT/name) for name in files},
    training_admission=False, launch_readiness=False,
    limitations=['Pure receipt/resource validation and exclusive claim contracts only.',
                 'No reviewed producer/launcher, private Ray lifecycle, or eight-rank audit yet.',
                 'Review flags require a subsequently reviewed producer; this is not an authentication boundary.',
                 'Source manifest coverage for native dependencies and full offline data identities remains to be reviewed.',
                 'Read-only port bind checks do not reserve ports; launcher must control startup race.',
                 'No model import, model forward, optimizer update, or test checkpoint in this validator.'])
with (ROOT/'reports/GPU_LAUNCH_GATE_R6_CONTRACTS.json').open('x') as out:
    json.dump(report, out, indent=2, allow_nan=False)
print(json.dumps(dict(status=report['status'], tests=result.testsRun, resource_gate_pass=resource_pass)))
