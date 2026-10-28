"""CPU negative contracts. All receipts are synthetic and live only in memory/tempdirs."""
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import gpu_launch_gate_r6 as gate


class LaunchBindingTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000.0
        self.run = Path('/synthetic/not-a-launch')
        self.config = {'trainer': {'resume_mode': 'disable', 'experiment_name':
            'sao-qwen35-9b-b64-dynamic-r6-gpu-probe-20261028'}}
        self.sources = {'/synthetic/source.py': 'a'*64}
        self.assets = {'/synthetic/weights': 'b'*64}
        self.resources = dict(observed_at=self.now, original_start_required_bytes=gate.START_BYTES,
            save_required_bytes=gate.SAVE_BYTES, original_resource_receipt_SHA=gate.RESOURCE_SHA,
            free_bytes=gate.START_BYTES, gpus=[dict(index=i, uuid=f'GPU-synthetic-{i}', memory_MiB=17,
            utilization=0) for i in range(8)], compute_processes=[], ray_processes=[],
            ports_available={str(p): True for p in gate.PORTS})
        self.receipt = dict(schema='r6-disposable-launch-v1', purpose='disposable_native_sp8_probe',
            training_admission=False, created_at=self.now, boot_id='synthetic-boot', run=str(self.run),
            config_SHA=gate.canonical_sha(self.config), source_manifest_SHA=gate.canonical_sha(self.sources),
            offline_asset_manifest_SHA=gate.canonical_sha(self.assets), resources=copy.deepcopy(self.resources),
            review=dict(existing_native_PI_evidence_verified=True, rank_audit_implementation_reviewed=True,
                private_ray_lifecycle_reviewed=True, hydra_both_phases_pass=True))

    def check(self):
        gate.validate_binding(self.receipt, self.config, self.sources, self.assets, self.run,
                              self.now, 'synthetic-boot', self.resources)

    def test_synthetic_boundary_pass(self):
        self.check()

    def test_binding_changes_rejected(self):
        for name in ('config_SHA', 'source_manifest_SHA', 'offline_asset_manifest_SHA', 'run',
                     'boot_id', 'schema', 'purpose'):
            with self.subTest(name=name):
                original = self.receipt[name]
                self.receipt[name] = 'tampered'
                with self.assertRaises(gate.GateError):
                    self.check()
                self.receipt[name] = original

    def test_stale_future_nonfinite_time_rejected(self):
        for value in (self.now-121, self.now+0.001, float('nan'), float('inf'), True, '1000'):
            with self.subTest(value=value):
                self.receipt['created_at'] = value
                with self.assertRaises(gate.GateError):
                    self.check()

    def test_review_pending_or_truthy_string_rejected(self):
        for key in self.receipt['review']:
            for value in (False, 'true', 1):
                with self.subTest(key=key, value=value):
                    self.receipt['review'][key] = value
                    with self.assertRaises(gate.GateError):
                        self.check()
                    self.receipt['review'][key] = True

    def test_training_not_admitted(self):
        self.receipt['training_admission'] = True
        with self.assertRaises(gate.GateError):
            self.check()

    def test_resume_forbidden_even_with_rebound_hash(self):
        self.config['trainer']['resume_mode'] = 'auto'
        self.receipt['config_SHA'] = gate.canonical_sha(self.config)
        with self.assertRaises(gate.GateError):
            self.check()

    def test_current_resources_cannot_reuse_past_pass(self):
        mutations = [
            ('free_bytes', gate.START_BYTES-1), ('original_start_required_bytes', 200*1024**3),
            ('save_required_bytes', 200*1024**3), ('original_resource_receipt_SHA', 'x'),
            ('observed_at', self.now-121), ('compute_processes', ['1,GPU-synthetic-0']),
            ('ray_processes', [123]), ('gpus', self.resources['gpus'][:7]),
            ('ports_available', {str(p): p != 6407 for p in gate.PORTS}),
            ('ports_available', {'6407': True}),
        ]
        for key, value in mutations:
            with self.subTest(key=key):
                original = self.resources[key]
                self.resources[key] = value
                with self.assertRaises(gate.GateError):
                    self.check()
                self.resources[key] = original

    def test_receipted_resources_must_also_pass(self):
        self.receipt['resources']['free_bytes'] = gate.START_BYTES-1
        with self.assertRaises(gate.GateError):
            self.check()

    def test_gpu_busy_identity_and_duplicate_rejected(self):
        for key, value in [('utilization', 1), ('memory_MiB', 65), ('memory_MiB', -1),
                           ('uuid', 'GPU-synthetic-1'), ('uuid', 'GPU-other'), ('index', 1)]:
            with self.subTest(key=key, value=value):
                original = self.resources['gpus'][0][key]
                self.resources['gpus'][0][key] = value
                with self.assertRaises(gate.GateError):
                    self.check()
                self.resources['gpus'][0][key] = original

    def test_manifest_bytes_and_escape(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('R6_TEST_TMPDIR')) as folder:
            root = Path(folder).resolve()
            path = root/'probe.py'
            path.write_bytes(b'original')
            manifest = {str(path): gate.file_sha(path)}
            gate.verify_manifest(manifest, (root,))
            path.write_bytes(b'changed')
            with self.assertRaises(gate.GateError):
                gate.verify_manifest(manifest, (root,))
            with self.assertRaises(gate.GateError):
                gate.verify_manifest({str(path): gate.file_sha(path)}, (root/'other',))
            with self.assertRaises(gate.GateError):
                gate.verify_manifest({}, (root,))

    def test_exclusive_attempt_consumption(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('R6_TEST_TMPDIR')) as folder:
            root = Path(folder).resolve()
            gate.claim_attempt(root, {'synthetic_contract_only': True})
            original = (root/'launch_claim.json').read_bytes()
            with self.assertRaises(FileExistsError):
                gate.claim_attempt(root, {'second_consumer': True})
            self.assertEqual((root/'launch_claim.json').read_bytes(), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
