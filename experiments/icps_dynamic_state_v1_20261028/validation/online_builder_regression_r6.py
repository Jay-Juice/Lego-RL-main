"""Run preserved SDK remapping and structural contracts against the new overlay."""
import hashlib
import json
import pathlib
import unittest

N = pathlib.Path(__file__).resolve().parents[1]
R = N.parent/'pi_repair_state_v2_20261015'


def main():
    from verl_patch.agent_loop import privileged_critic_builder as builder
    assert pathlib.Path(builder.__file__).resolve() == N/'runtime/privileged_critic_builder.py'
    counts, sources = {}, {}
    for pattern in ['test_pi_split_alias.py', 'test_pi_sdk_proven_alias.py', 'test_structural_pi_v1.py']:
        suite = unittest.defaultTestLoader.discover(str(R/'tests'), pattern=pattern)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        assert result.testsRun > 0 and result.wasSuccessful(), pattern
        counts[pattern] = result.testsRun
        sources[pattern] = hashlib.sha256((R/'tests'/pattern).read_bytes()).hexdigest()
    report = dict(status='passed', counts=counts, total=sum(counts.values()),
                  actual_overlay_builder=str(pathlib.Path(builder.__file__).resolve()),
                  builder_sha256=hashlib.sha256(pathlib.Path(builder.__file__).read_bytes()).hexdigest(),
                  preserved_test_source_sha256=sources, gpu=False, optimizer=False)
    with (N/'reports/ONLINE_BUILDER_R6_REGRESSION.json').open('x') as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
