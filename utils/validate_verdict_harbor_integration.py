#!/usr/bin/env python3
"""Isolated CPU Harbor trials exercising the generated verifier, without an LLM."""
import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from prepare_swesmith_harbor import RUN_TESTS, TEST_SH
from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    image = 'lego-verdict-v3-integration:' + hashlib.sha256(str(args.output.resolve()).encode()).hexdigest()[:12]
    cases = {
        'pass': ('def test_case(): assert True\n', 1),
        'fail': ('def test_case(): assert False\n', 0),
        'collection': ('raise RuntimeError("deliberate collection failure")\n', None),
        'timeout': ('import time\ndef test_case(): time.sleep(360)\n', None),
        'missing': ('def test_case(): assert True\n', None),
        'setup_error': ('def setup_function(): raise RuntimeError("missing tool")\ndef test_case(): pass\n', None),
        'skipped': ('import pytest\n@pytest.mark.skip(reason="no executed test")\ndef test_case(): pass\n', None),
        'source_boundary': ('def test_case(): assert True\n', None),
        'cli_path': ('import pathlib, shutil, sys\ndef test_case():\n assert pathlib.Path(shutil.which("python")).resolve() == pathlib.Path(sys.executable).resolve()\n', 1),
    }
    results = {}
    for name, (code, expected) in cases.items():
        task = args.output / 'tasks' / ('audit-verdict-' + name)
        shutil.copytree(args.template, task)
        tests = task / 'tests'
        # Existing task stays untouched. Fixtures live only in this fresh copy.
        payload = tests / 'payload'
        # This is a newly created isolated fixture tree, never the source task.
        assert payload.resolve().is_relative_to(args.output.resolve())
        shutil.rmtree(payload)
        payload.mkdir()
        fixture_name = 'business_module.py' if name == 'source_boundary' else 'test_audit_verdict.py'
        fixture = payload / fixture_name
        fixture.write_text(code)
        (tests / 'config.json').write_text(json.dumps({
            'FAIL_TO_PASS': [fixture_name+'::test_case'], 'PASS_TO_PASS': []}))
        (tests / 'run_tests.py').write_text(RUN_TESTS)
        (tests / 'test.sh').write_text(TEST_SH if name != 'missing' else '#!/bin/bash\nexit 0\n')
        # Own image tag: never let Harbor build over a historical task image.
        toml = task/'task.toml'
        toml.write_text(re.sub(r'docker_image = "[^"]+"',
            f'docker_image = "{image}"', toml.read_text()))
        if name == 'pass':
            if subprocess.run(['docker','image','inspect',image],capture_output=True).returncode == 0:
                raise FileExistsError(f'Integration image already exists: {image}')
            with (args.output/'image-build.log').open('w') as log:
                subprocess.run(['docker','build','--network','none','--pull=false',
                    '--label','lego.verdict.integration=v3-20260929', '-t',image,
                    str(task/'environment')],stdout=log,stderr=subprocess.STDOUT,check=True)
        config = TrialConfig.model_validate({
            'task': {'path': str(task)}, 'trial_name': 'audit-' + name,
            'trials_dir': str(args.output / 'trials'), 'agent': {'name': 'nop'},
            # Harbor delete=True also removes the prebuilt task image. Keep images;
            # delete=False still executes compose down for this trial's containers.
            'environment': {'type': 'docker', 'force_build': False, 'delete': False},
            'predict_patch': {'enabled': False},
        })
        trial = await Trial.create(config)
        result = await trial.run()
        reward = result.verifier_result.rewards.get('reward') if result.verifier_result else None
        status_file = args.output / 'trials' / ('audit-' + name) / 'verifier/grading_status.json'
        status = json.loads(status_file.read_text()) if status_file.exists() else None
        assert reward == expected, (name, reward, expected)
        if name in ('collection', 'timeout', 'setup_error', 'skipped', 'source_boundary'):
            assert status and status['status'] == 'unresolved', (name, status)
        if expected is not None:
            assert status and status['status'] == 'scored', (name, status)
        results[name] = {'reward': reward, 'grading_status': status,
                         'exception': result.exception_info.exception_type if result.exception_info else None}
        (args.output / 'results.json').write_text(json.dumps(results, indent=2))
        print(json.dumps({name: results[name]}), flush=True)
    (args.output / 'PASS.json').write_text(json.dumps({
        'cases': results, 'generated_verifier_sha256': hashlib.sha256(RUN_TESTS.encode()).hexdigest(),
        'scope': 'Real Harbor Trial with Docker and nop agent; no eight-GPU training claim'}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
