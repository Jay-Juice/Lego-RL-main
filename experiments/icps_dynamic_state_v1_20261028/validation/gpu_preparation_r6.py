"""CPU-only fixture/source/resource inventory; does not launch or install anything."""
import hashlib
import json
import shutil
import socket
import subprocess
from pathlib import Path

N = Path(__file__).resolve().parents[1]
B = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
R = B/'experiments/pi_repair_state_v2_20261015'
F = B/'experiments/icps_v11_full97_sao_20261024_r2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    return subprocess.check_output(args, text=True, timeout=60).strip()


def main():
    from transformers import AutoTokenizer
    from gpu_probe_r6 import cpu_contracts
    from verl_patch.agent_loop import privileged_critic_builder
    assert Path(privileged_critic_builder.__file__).resolve() == N/'runtime/privileged_critic_builder.py'
    freeze = json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())
    for path, expected in freeze['source_SHA'].items():
        assert sha(N/path) == expected, path
    provenance = json.loads((N/'PROVENANCE.json').read_text())
    for path, expected in provenance['source_files_SHA256'].items():
        assert sha(F/path.replace('\\', '/')) == expected, path
    native_files = [
        'src/verl_patch/models/qwen3_5_token_classification.py',
        'third_party/verl/verl/trainer/ppo/core_algos.py',
        'third_party/verl/verl/workers/engine/veomni/transformer_impl.py',
        'third_party/verl/verl/workers/config/critic.py',
        'third_party/verl/verl/workers/config/actor.py',
    ]
    source_rows = []
    for path in native_files:
        row = dict(path=path, baseline_exists=(B/path).is_file(), runtime_exists=(R/path).is_file())
        if row['baseline_exists'] and row['runtime_exists']:
            row.update(baseline_SHA=sha(B/path), runtime_SHA=sha(R/path))
            row['equal'] = row['baseline_SHA'] == row['runtime_SHA']
        source_rows.append(row)
    inherited = ['runtime/ray_trainer.py', 'runtime/engine_utils.py', 'src/formal_packing.py',
                 'src/formal_storage.py', 'src/formal_checkpoint.py']
    for path in inherited:
        assert sha(N/path) == sha(F/path), path
    tokenizer = AutoTokenizer.from_pretrained(B/'Qwen3.5-9B', local_files_only=True)
    contracts = cpu_contracts(tokenizer)
    pids = run('nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader')
    memory = [int(x) for x in run('nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits').splitlines()]
    ports = {}
    for port in (6407, 8307, 8265):
        try:
            with socket.socket() as sock:
                sock.bind(('0.0.0.0', port))
            ports[str(port)] = True
        except OSError:
            ports[str(port)] = False
    ray_absent = all(subprocess.run(['pgrep', '-x', name], stdout=subprocess.DEVNULL).returncode == 1
                     for name in ('raylet', 'gcs_server'))
    original = json.loads((F/'preflight/RESOURCE_AND_SOURCE.json').read_text())
    required = original['minimum_before_start_bytes']
    assert required >= 250*1024**3+189686470567
    free = shutil.disk_usage(N).free
    report = dict(status='cpu_preparation_complete_not_GPU_acceptance', GPU_launched=False,
        contracts=contracts, frozen_sources_exact=7, old_sources_exact=len(provenance['source_files_SHA256']),
        inherited_training_logic_exact=inherited, historical_native_source_inventory=source_rows,
        selected_native_source_parity_pass=all(row.get('equal', False) for row in source_rows),
        resources=dict(free_bytes=free, original_start_required_bytes=required,
            deficit_bytes=max(0, required-free), original_resource_receipt_SHA=sha(F/'preflight/RESOURCE_AND_SOURCE.json'),
            save_required_bytes=189686470567+210*1024**3,
            all8GPUs_idle=not pids and len(memory)==8 and max(memory)<1000,
            gpu_memory_MiB=memory, ports_available=ports, Ray_absent=ray_absent,
            disk_gate_pass=free>=required),
        training_admission=False, launch_receipt_created=False,
        limitations=['CPU batch contract is not GPU evidence.',
                     'Source inventory only covers listed native files; unresolved differences require review.',
                     'Pinned full dataset/images and actual eight-rank head/freeze still require fresh launch audit.'])
    with (N/'reports/GPU_PREPARATION_R6_R3.json').open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
