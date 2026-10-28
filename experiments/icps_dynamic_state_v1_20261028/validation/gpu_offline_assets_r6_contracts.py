"""Synthetic negatives plus optional actual readonly cached-asset hashing."""
import copy
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

N = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(N/'src'))
import gpu_offline_assets_r6 as assets
from gpu_launch_gate_r6 import GateError, canonical_sha, file_sha


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=N/'validation')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.model, self.data = self.root/'model', self.root/'data'
        self.model.mkdir(); self.data.mkdir()
        for name in assets.MODEL_NAMES:
            (self.model/name).write_text('{}' if name.endswith('.json') else 'fixture')
        self.index = {'metadata': {'total_size': 8}, 'weight_map': {}}
        for i, name in enumerate(sorted(n for n in assets.MODEL_NAMES if n.endswith('.safetensors'))):
            tensor = 'tensor'+str(i)
            header = {tensor: dict(dtype='BF16', shape=[1], data_offsets=[0,2])}
            self.write_shard(name, header)
            self.index['weight_map'][tensor] = name
        self.write_index()
        (self.model/'config.json').write_text('{"model_type":"qwen3_5"}')
        for name in assets.DATA_NAMES:
            (self.data/name).write_bytes(b'PAR1fixturePAR1')
        self.config = {'actor_rollout_ref':{'model':{'path':str(self.model)}},
                       'critic':{'model':{'path':str(self.model)}},
                       'data':dict(train_files=str(self.data/assets.DATA_NAMES[0]),
                                   val_files=str(self.data/assets.DATA_NAMES[1]))}

    def write_shard(self, name, header, payload=b'xx'):
        raw = json.dumps(header).encode()
        (self.model/name).write_bytes(struct.pack('<Q',len(raw))+raw+payload)

    def write_index(self):
        (self.model/'model.safetensors.index.json').write_text(json.dumps(self.index))

    def collect(self):
        return assets.collect(self.config, self.model, self.data)

    def test_complete_and_manifest_identity(self):
        manifest, info = self.collect()
        self.assertEqual(info['file_count'], 18)
        self.assertEqual(info['tensor_count'], 4)
        assets.verify_exact(manifest, manifest.copy())
        for changed in ({**manifest, str(self.root/'extra'): '0'*64},
                        {k:v for k,v in manifest.items() if not k.endswith('README.md')}):
            with self.assertRaises(GateError): assets.verify_exact(changed, manifest)

    def test_extra_and_missing_model_input(self):
        p=self.model/'generation_config.json'; p.write_text('{}')
        with self.assertRaisesRegex(GateError, 'missing or extra'): self.collect()
        p.unlink(); (self.model/'tokenizer.json').unlink()
        with self.assertRaisesRegex(GateError, 'missing or extra'): self.collect()

    def test_index_shard_escape_and_missing(self):
        for name in ('../escape.safetensors', 'absent.safetensors'):
            self.index['weight_map']['tensor0'] = name; self.write_index()
            with self.assertRaisesRegex(GateError, 'shard set'): self.collect()

    def test_index_tensor_mapping(self):
        self.index['weight_map']['invented'] = self.index['weight_map'].pop('tensor0')
        self.write_index()
        with self.assertRaisesRegex(GateError, 'tensor mapping'): self.collect()

    def test_total_size(self):
        self.index['metadata']['total_size'] = True; self.write_index()
        with self.assertRaisesRegex(GateError, 'total size'): self.collect()

    def test_corrupt_headers_and_layout(self):
        name = sorted(self.index['weight_map'].values())[0]
        bad = [dict(dtype='BF16',shape=[True],data_offsets=[0,2]),
               dict(dtype='BF16',shape=[1],data_offsets=[1,3]),
               dict(dtype='BF16',shape=[2],data_offsets=[0,2]),
               dict(dtype='UNKNOWN',shape=[1],data_offsets=[0,2])]
        for header in bad:
            self.write_shard(name, {'tensor0':header})
            with self.assertRaises(GateError): self.collect()
        (self.model/name).write_bytes(struct.pack('<Q', 2**40))
        with self.assertRaisesRegex(GateError,'header bound'): self.collect()

    def test_shard_truncation(self):
        name=sorted(self.index['weight_map'].values())[0]
        p=self.model/name; p.write_bytes(p.read_bytes()[:-1])
        with self.assertRaisesRegex(GateError,'length mismatch'): self.collect()

    def test_json_duplicate_and_nonfinite(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(GateError): assets.read_json(raw)

    def test_config_model_and_data_binding(self):
        original=copy.deepcopy(self.config)
        for group,key in (('data','train_files'),('data','val_files')):
            self.config=copy.deepcopy(original); self.config[group][key]='/unapproved'
            with self.assertRaises(GateError): self.collect()
        self.config=copy.deepcopy(original); self.config['critic']['model']['path']='/unapproved'
        with self.assertRaises(GateError): self.collect()

    def test_parquet_and_hash_drift(self):
        manifest,_=self.collect()
        (self.model/'chat_template.jinja').write_text('changed')
        with self.assertRaisesRegex(GateError,'hash drift'): assets.verify_exact(manifest,manifest.copy())
        (self.data/assets.DATA_NAMES[0]).write_bytes(b'xxxxfixturexxxx')
        with self.assertRaisesRegex(GateError,'parquet envelope'): self.collect()

    def test_mutation_between_header_check_and_hash(self):
        original = assets.stable_sha
        target = self.model/sorted(self.index['weight_map'].values())[0]
        mutated = False
        def changing_hash(path):
            nonlocal mutated
            if not mutated:
                mutated = True
                # Corrupt the previously validated shard before hashing it. Each
                # individual hash remains stable, so the whole-pass check matters.
                target.write_bytes(target.read_bytes()+b'bad')
            return original(path)
        with patch.object(assets, 'stable_sha', changing_hash):
            with self.assertRaisesRegex(GateError, 'across inspection'): self.collect()

    @unittest.skipUnless(os.name == 'posix', 'Linux symlink contract')
    def test_symlink_file_cache_and_parent(self):
        p=self.model/'README.md'; p.unlink(); p.symlink_to(self.model/'LICENSE')
        with self.assertRaisesRegex(GateError,'symlinks'): self.collect()
        p.unlink(); p.write_text('fixture')
        (self.model/'.cache').symlink_to(self.data, target_is_directory=True)
        with self.assertRaisesRegex(GateError,'symlinks'): self.collect()
        (self.model/'.cache').unlink()
        alias=self.root/'alias'; alias.symlink_to(self.model,target_is_directory=True)
        with self.assertRaisesRegex(GateError,'symlinks'): assets.expected_assets(alias,self.data)


if __name__ == '__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    if not result.wasSuccessful(): raise SystemExit(1)
    if '--actual-assets' in sys.argv:
        ref=N/'reports/GPU_PROBE_R6_HYDRA_PARITY.json'
        assert file_sha(ref)=='42d0c0e14303b644e74eef1603da798be63f71c56c928a9739b2fa6b44928208'
        manifest, info=assets.collect(json.loads(ref.read_text())['complete_actual_config'])
        queue=N/'logs/gpu_offline_assets_r6_contracts_r2'
        with (queue/'offline_asset_manifest.json').open('x') as out: json.dump(manifest,out,indent=2)
        frozen=json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA']
        assert all(file_sha(N/p)==h for p,h in frozen.items())
        old=json.loads((N/'PROVENANCE.json').read_text())['source_files_SHA256']
        f=assets.B/'experiments/icps_v11_full97_sao_20261024_r2'
        assert all(file_sha(f/p.replace('\\','/'))==h for p,h in old.items())
        report=dict(status='OFFLINE_ASSET_COMPONENT_PASS_NOT_LAUNCH_ADMISSION',
            tests_run=result.testsRun, tests_skipped=len(result.skipped), actual_cached_assets=info,
            asset_manifest_SHA=canonical_sha(manifest), frozen_sources_exact=len(frozen),old_sources_exact=len(old),
            source_SHA={p:file_sha(N/p) for p in ('src/gpu_offline_assets_r6.py',
                'validation/gpu_offline_assets_r6_contracts.py','ops/gpu_offline_assets_r6_contracts.sh')},
            CUDA_initialized=False,Ray_initialized=False,model_constructed=False,optimizer_steps=0,
            production_receipt_created=False, consumer_integrated=False,training_admitted=False,
            limitations=['Current asset identity, not historical binary identity or formal dataset/image admission.',
              'Parquet envelope/hash only: no rows, task IDs, labels or scores read.',
              'Only safetensors metadata and file hashes read; no model tensors constructed.',
              'The download cache is excluded; this component executes no loader.',
              'Shared dependency policy, reviewed producer and actual Ray/GPU acceptance remain pending.'])
        assert 'torch' not in sys.modules and 'ray' not in sys.modules
        with (N/'reports/GPU_OFFLINE_ASSETS_R6_CONTRACTS_R2.json').open('x') as out: json.dump(report,out,indent=2)
        print(json.dumps(report))
