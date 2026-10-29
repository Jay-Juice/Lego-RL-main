"""Isolated bridge contracts; no real proxy/Harbor/Actor/GPU acceptance claim."""
import hashlib
import json
import pathlib
import sys
import unittest

N = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(N/'tests'), str(N/'src'), str(N/'core')]
import test_dynamic_runtime_r6 as contracts


def run():
    freeze = json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())
    for f, h in freeze['source_SHA'].items():
        assert hashlib.sha256((N/f).read_bytes()).hexdigest() == h
    counts = {}
    for mode in ['byte', 'actual_Qwen']:
        if mode == 'actual_Qwen':
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(N.parents[1]/'Qwen3.5-9B', local_files_only=True)
            contracts.base.Tok = lambda: tok
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(contracts.BridgeContracts))
        assert result.wasSuccessful() and result.testsRun == 8
        counts[mode] = result.testsRun
    source = {f: hashlib.sha256((N/f).read_bytes()).hexdigest() for f in
              ['src/dynamic_runtime_r6.py', 'tests/test_dynamic_runtime_r6.py',
               'validation/online_bridge_r6.py']}
    report = dict(status='ISOLATED_BRIDGE_CONTRACTS_PASS', tests=counts, source=source,
                  frozen_generator_unchanged=True, runtime_dispatch_enabled=False,
                  actual_proxy_tested=False, Harbor_tested=False, GPU_jobs=0,
                  training_admitted=False,
                  limitations=['Synthetic snapshots and direct bridge calls only.',
                               'Actual proxy, metadata cleanup wiring, Docker/Harbor and builder remain pending.'])
    (N/'reports/ONLINE_BRIDGE_R6_CONTRACTS.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__': run()
