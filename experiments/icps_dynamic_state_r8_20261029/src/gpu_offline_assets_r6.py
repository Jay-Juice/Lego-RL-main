"""Exact cached asset inventory for R6 preparation, never launch approval.

Read safetensors headers and stream file hashes without importing a model or
reading tensor values into Python objects. The caller must independently pin
the resulting manifest to reviewed evidence before a future consumer uses it.
The Hugging Face download cache is not an input; no loader executes here.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

from gpu_launch_gate_r6 import B, require

MODEL_NAMES = frozenset({'.gitattributes', 'LICENSE', 'README.md',
    'chat_template.jinja', 'config.json', 'merges.txt',
    'model.safetensors.index.json', 'preprocessor_config.json', 'tokenizer.json',
    'tokenizer_config.json', 'video_preprocessor_config.json', 'vocab.json',
    *('model.safetensors-%05d-of-00004.safetensors' % i for i in range(1, 5))})
DATA_NAMES = ('swesmith_python_full_v7_verdict_v6_20260930.parquet',
              'swesmith_python_full_v7_smoke1.parquet')
DTYPE_BYTES = {'BF16': 2, 'F16': 2, 'F32': 4, 'F64': 8, 'I64': 8,
               'I32': 4, 'I16': 2, 'I8': 1, 'U8': 1, 'BOOL': 1}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read_json(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda x: require(False, 'nonfinite JSON'))


def plain(path, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'asset path must be canonical without symlinks')
    require(path.is_dir() if directory else path.is_file(), 'asset file type')
    return path


def identity(path):
    stat = plain(path).stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def stable_sha(path):
    path = plain(path)
    before = identity(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    require(before == identity(path), 'asset changed during hashing')
    return digest


def validate_config_paths(config, model, data):
    require(config['actor_rollout_ref']['model']['path'] == str(model), 'actor model path')
    require(config['critic']['model']['path'] == str(model), 'critic model path')
    require(config['data']['train_files'] == str(data/DATA_NAMES[0]), 'training data path')
    require(config['data']['val_files'] == str(data/DATA_NAMES[1]), 'validation data path')


def header_inventory(path):
    """Require a complete, contiguous safetensors layout; return tensor names only."""
    path = plain(path)
    with path.open('rb') as stream:
        prefix = stream.read(8)
        require(len(prefix) == 8, 'truncated safetensors length')
        size = struct.unpack('<Q', prefix)[0]
        require(2 <= size <= 16 * 1024 * 1024, 'safetensors header bound')
        raw = stream.read(size)
        require(len(raw) == size, 'truncated safetensors header')
    header = read_json(raw)
    require(type(header) is dict, 'safetensors header object')
    if '__metadata__' in header:
        require(type(header['__metadata__']) is dict and
                all(type(k) is str and type(v) is str for k,v in header['__metadata__'].items()),
                'safetensors metadata')
    tensors = {k:v for k,v in header.items() if k != '__metadata__'}
    require(bool(tensors), 'empty shard')
    spans = []
    for name, value in tensors.items():
        require(type(value) is dict and set(value) == {'dtype', 'shape', 'data_offsets'},
                'tensor header keys')
        require(value['dtype'] in DTYPE_BYTES, 'unreviewed tensor dtype')
        shape, offsets = value['shape'], value['data_offsets']
        require(type(shape) is list and all(type(x) is int and x >= 0 for x in shape), 'tensor shape')
        require(type(offsets) is list and len(offsets) == 2 and
                all(type(x) is int and x >= 0 for x in offsets), 'tensor offsets')
        start, end = offsets
        require(end-start == math.prod(shape)*DTYPE_BYTES[value['dtype']], 'tensor byte span')
        spans.append((start, end, name))
    cursor = 0
    for start, end, _ in sorted(spans):
        require(start == cursor, 'tensor overlap or hole')
        cursor = end
    require(8+size+cursor == path.stat().st_size, 'shard length mismatch')
    return set(tensors), cursor


def expected_assets(model, data):
    model, data = plain(model, directory=True), plain(data, directory=True)
    actual = {p.name for p in model.iterdir()}
    require(actual - {'.cache'} == MODEL_NAMES, 'model missing or extra file')
    if '.cache' in actual:
        plain(model/'.cache', directory=True)
    paths = [plain(model/n) for n in sorted(MODEL_NAMES)]
    paths += [plain(data/n) for n in DATA_NAMES]
    return paths


def collect(config, model=None, data=None):
    model = B/'Qwen3.5-9B' if model is None else Path(model)
    data = B/'data' if data is None else Path(data)
    validate_config_paths(config, model, data)
    paths = expected_assets(model, data)
    before = {p: identity(p) for p in paths}
    # Bind metadata bytes used for structural checks to the final hashed snapshot.
    metadata = {p: p.read_bytes() for p in paths if p.suffix == '.json'}
    index = read_json(metadata[model/'model.safetensors.index.json'])
    require(set(index) == {'metadata', 'weight_map'}, 'index fields')
    weights = index['weight_map']
    require(type(weights) is dict and bool(weights), 'empty weight map')
    shard_names = {n for n in MODEL_NAMES if n.endswith('.safetensors')}
    require(set(weights.values()) == shard_names, 'index shard set')
    total = 0
    for name in sorted(shard_names):
        tensors, count = header_inventory(model/name)
        require(tensors == {k for k,v in weights.items() if v == name}, 'index tensor mapping')
        total += count
    require(type(index['metadata']['total_size']) is int and
            index['metadata']['total_size'] == total, 'index total size')
    require(read_json(metadata[model/'config.json'])['model_type'] == 'qwen3_5', 'model type')
    for path in (data/n for n in DATA_NAMES):
        with path.open('rb') as stream:
            first = stream.read(4)
            stream.seek(-4, 2)
            require(first == b'PAR1' and stream.read(4) == b'PAR1', 'parquet envelope')
    manifest = {str(p): stable_sha(p) for p in paths}
    require(set(manifest) == {str(p) for p in expected_assets(model, data)}, 'asset set changed')
    require(before == {p: identity(p) for p in paths}, 'asset changed across inspection and hashing')
    require(all(manifest[str(p)] == hashlib.sha256(raw).hexdigest() for p,raw in metadata.items()),
            'asset metadata changed')
    return manifest, dict(file_count=len(manifest), shard_count=len(shard_names),
                         tensor_count=len(weights), tensor_bytes=total,
                         parquet_envelope_only=True, training_admitted=False)


def verify_exact(manifest, expected):
    """Check exact identity against independently reviewed assets, including extras."""
    require(type(manifest) is dict and manifest == expected, 'offline manifest identity mismatch')
    for name, digest in manifest.items():
        require(stable_sha(Path(name)) == digest, 'offline asset hash drift')
