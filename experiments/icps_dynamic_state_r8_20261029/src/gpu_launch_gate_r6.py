"""Fail-closed receipt consumer for the disposable R6 probe, not a launcher.

The scoped disposable launcher produces a receipt from existing evidence,
bind its hash independently, and pass fresh observations immediately before use.
This protects against stale/mismatched evidence, not a malicious local owner.
Only standard-library imports: negative contracts require no CUDA/model imports.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import time

B = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
N = B / 'experiments/icps_dynamic_state_r8_20261029'
R = B / 'experiments/pi_repair_state_v2_20261015'
START_BYTES = 458392574347
SAVE_BYTES = 415172253607
RESOURCE_SHA = '7ce0d305cb9e53e39f21f2424afc53100b7297fc6f8ce80eb712fd67b02a40aa'
PORTS = {6407, 8307, 8265}
MAX_AGE = 120


class GateError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                  ensure_ascii=True, allow_nan=False).encode())


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fresh(timestamp, now, name):
    require(type(timestamp) in (int, float) and math.isfinite(timestamp), name+' invalid time')
    require(0 <= now-timestamp <= MAX_AGE, name+' expired or future')


def validate_resources(value, now):
    fresh(value['observed_at'], now, 'resources')
    require(value['original_start_required_bytes'] == START_BYTES, 'start reserve altered')
    require(value['save_required_bytes'] == SAVE_BYTES, 'save reserve altered')
    require(value['original_resource_receipt_SHA'] == RESOURCE_SHA, 'original reserve identity')
    require(type(value['free_bytes']) is int and value['free_bytes'] >= START_BYTES, 'disk reserve')
    rows = value['gpus']
    require(len(rows) == 8 and {r['index'] for r in rows} == set(range(8)), 'eight GPU identities')
    require(len({r['uuid'] for r in rows}) == 8 and all(r['uuid'].startswith('GPU-') for r in rows), 'GPU UUIDs')
    for row in rows:
        require(type(row['memory_MiB']) is int and 0 <= row['memory_MiB'] <= 64, 'GPU memory occupied')
        require(type(row['utilization']) is int and row['utilization'] == 0, 'GPU busy')
    require(value['compute_processes'] == [], 'GPU processes present')
    require(value['ray_processes'] == [], 'Ray processes present')
    require(set(value['ports_available']) == {str(p) for p in PORTS}, 'port inventory')
    require(all(v is True for v in value['ports_available'].values()), 'port occupied')


def validate_binding(receipt, config, sources, assets, run, now, boot_id, resources):
    """Pure validation, also used with clearly synthetic temporary CPU fixtures."""
    require(receipt['schema'] == 'r6-disposable-launch-v1', 'receipt schema')
    require(receipt['purpose'] == 'disposable_native_sp8_probe', 'receipt purpose')
    require(receipt['training_admission'] is False, 'probe cannot admit training')
    fresh(receipt['created_at'], now, 'receipt')
    require(receipt['boot_id'] == boot_id, 'host boot changed')
    require(receipt['run'] == str(run), 'run mismatch')
    require(receipt['config_SHA'] == canonical_sha(config), 'resolved config mismatch')
    require(receipt['source_manifest_SHA'] == canonical_sha(sources), 'source binding mismatch')
    require(receipt['offline_asset_manifest_SHA'] == canonical_sha(assets), 'asset binding mismatch')
    require(receipt['review']['existing_native_PI_evidence_verified'] is True, 'existing native/PI evidence pending')
    require(receipt['review']['rank_audit_implementation_reviewed'] is True, 'rank audit not reviewed')
    require(receipt['review']['private_ray_lifecycle_reviewed'] is True, 'private Ray lifecycle pending')
    require(receipt['review']['hydra_both_phases_pass'] is True, 'Hydra parity pending')
    require(config['trainer']['resume_mode'] == 'disable', 'resume forbidden')
    require(config['trainer']['experiment_name'] == 'sao-qwen35-9b-b64-dynamic-r6-gpu-probe-20261028', 'experiment mismatch')
    validate_resources(receipt['resources'], now)
    validate_resources(resources, now)
    require([(r['index'], r['uuid']) for r in resources['gpus']] ==
            [(r['index'], r['uuid']) for r in receipt['resources']['gpus']], 'GPU identities changed')


def verify_manifest(manifest, roots):
    require(bool(manifest), 'empty manifest')
    for name, expected in manifest.items():
        path = Path(name)
        require(path.is_absolute() and path.resolve() == path, 'noncanonical manifest path')
        require(any(path.is_relative_to(root) for root in roots), 'manifest escapes approved roots')
        require(re.fullmatch('[0-9a-f]{64}', expected) is not None, 'invalid SHA')
        require(path.is_file() and file_sha(path) == expected, 'file SHA mismatch: '+name)


def collect_resources():
    """Read-only fresh observation. Ports are checked, not reserved; launcher owns race control."""
    output = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.used,utilization.gpu',
                                      '--format=csv,noheader,nounits'], text=True, timeout=15)
    rows = []
    for line in output.splitlines():
        index, uuid, memory, utilization = [x.strip() for x in line.split(',')]
        rows.append(dict(index=int(index), uuid=uuid, memory_MiB=int(memory), utilization=int(utilization)))
    processes = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid',
                                         '--format=csv,noheader,nounits'], text=True, timeout=15).splitlines()
    ray_processes = []
    for process in Path('/proc').glob('[0-9]*'):
        try:
            executable = (process/'comm').read_text().strip()
            if executable in ('raylet', 'gcs_server'):
                ray_processes.append(int(process.name))
        except FileNotFoundError:
            pass
    ports = {}
    for port in sorted(PORTS):
        with socket.socket() as sock:
            try:
                sock.bind(('0.0.0.0', port))
                ports[str(port)] = True
            except OSError:
                ports[str(port)] = False
    stat = os.statvfs(N)
    reserve = B/'experiments/icps_v11_full97_sao_20261024_r2/preflight/RESOURCE_AND_SOURCE.json'
    require(file_sha(reserve) == RESOURCE_SHA, 'historical resource receipt changed')
    return dict(observed_at=time.time(), original_start_required_bytes=START_BYTES,
                save_required_bytes=SAVE_BYTES, original_resource_receipt_SHA=RESOURCE_SHA,
                free_bytes=stat.f_bavail*stat.f_frsize, gpus=sorted(rows, key=lambda r: r['index']),
                compute_processes=processes, ray_processes=ray_processes, ports_available=ports)


def claim_attempt(run, claim):
    """Exclusive creation is the final boundary; a second consumer cannot launch."""
    with (run/'launch_claim.json').open('x') as stream:
        json.dump(claim, stream, indent=2, allow_nan=False)


def consume(config):
    """Validate current files and resources, then atomically claim this one attempt.

    Called before ray.init. Any failed/used attempt requires a new run and receipt.
    It never starts Ray, imports CUDA, saves weights, or deletes anything.
    """
    require(os.name == 'posix', 'Linux launch only')
    run = Path(os.environ['ICPS_FORMAL_RUN_DIR'])
    require(run.parent == N/'runs' and re.fullmatch(r'gpu-r6-[0-9a-f]{16}', run.name), 'unique run namespace')
    require(run.resolve() == run, 'run symlink')
    require(Path(config['trainer']['default_local_dir']) == run/'NEVER_SAVE_CHECKPOINT', 'checkpoint namespace')
    require(not (run/'NEVER_SAVE_CHECKPOINT').exists(), 'checkpoint reuse')
    require(not (run/'result.json').exists() and not (run/'launch_claim.json').exists(), 'attempt already used')
    raw = (run/'launch_receipt.json').read_bytes()
    require(digest_bytes(raw) == os.environ.get('ICPS_R6_LAUNCH_RECEIPT_SHA'), 'independent receipt SHA missing/mismatch')
    receipt = json.loads(raw)
    sources = json.loads((run/'source_manifest.json').read_text())
    assets = json.loads((run/'offline_asset_manifest.json').read_text())
    verify_manifest(sources, (N, R, B/'src', B/'third_party', B/'.venv',
        Path('/home/ubuntu/.local/share/uv/python/cpython-3.12.3-linux-x86_64-gnu')))
    from gpu_launch_r6 import verify_evidence
    verify_evidence(sources)
    verify_manifest(assets, (B/'Qwen3.5-9B', B/'data'))
    required = {str(p) for folder in ('runtime', 'src', 'core') for p in (N/folder).rglob('*.py')}
    required.update(str(N/p) for p in ('ops/GPU_PROBE_R6.env', 'CANDIDATE_FREEZE_R6_SESSION.json'))
    require(required <= sources.keys(), 'incomplete overlay source manifest')
    frozen = json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA']
    require(all(sources.get(str(N/k)) == v for k, v in frozen.items()), 'frozen generator mismatch')
    weights = set((B/'Qwen3.5-9B').glob('*.safetensors'))
    require(bool(weights) and {str(p) for p in weights} <= assets.keys(), 'offline model shards incomplete')
    require(str(B/'Qwen3.5-9B/config.json') in assets, 'offline model config missing')
    # Observation follows potentially lengthy asset hashing, so it cannot expire during hashing.
    resources = collect_resources()
    now = time.time()
    validate_binding(receipt, config, sources, assets, run, now,
                     Path('/proc/sys/kernel/random/boot_id').read_text().strip(), resources)
    claim = dict(receipt_SHA=digest_bytes(raw), config_SHA=canonical_sha(config),
                 consumed_at=now, pid=os.getpid(), run=str(run), fresh_resources=resources,
                 training_admission=False)
    claim_attempt(run, claim)
    return claim
