#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mode=${1:?smoke or train}
case "$mode" in
  diagnostic_r3) config=pi_v2_resume_diagnostic_r3_20261015.env ;;
  diagnostic_r2) config=pi_v2_resume_diagnostic_r2_20261015.env ;;
  diagnostic) config=pi_v2_resume_diagnostic_20261015.env ;;
  acceptance) config=pi_v2_acceptance_20261015.env ;;
  smoke) echo "Use the isolated validation entry, not an inherited smoke launcher" >&2; exit 2 ;;
  train) config=sao_b64_pi_repair_state_v2_20261015.env ;;
  *) exit 2 ;;
esac
cd "$root"
mkdir -p logs
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$root/src:$root/third_party/verl:$root/third_party/harbor/src:$root"
export GLOO_SOCKET_IFNAME=eno1 TP_SOCKET_IFNAME=eno1 NCCL_SOCKET_IFNAME=eno1
export DOCKER_HOST=unix:///var/run/docker.sock
export TMPDIR=/tmp/lpi26
export LEGO_RL_ROOT="$root"
# Bind every future checkpoint/audit to this deployment manifest, not a guessed revision.
export PI_SOURCE_REVISION=$(sha256sum VERSION_SOURCE_SHA256.json | cut -d' ' -f1)
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B utils/validate_pi_source.py
stamp=$(date +%Y%m%d-%H%M%S)
log="$root/logs/${mode}_launcher_${stamp}.log"
exit_file="$root/logs/${mode}_launcher_${stamp}.exit"
printf '%s\n' "$log" > "$root/logs/${mode}_current_launcher.txt"
printf '%s\n' "$$" > "$root/logs/${mode}_launcher.pid"
trap 'code=$?; printf "%s\n" "$code" > "$exit_file"' EXIT
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import importlib.util, os, pathlib, subprocess, shutil
r=pathlib.Path(os.environ['LEGO_RL_ROOT']).resolve()
if shutil.disk_usage(r).free < 200 * 1024**3:
    raise RuntimeError('Less than 200 GiB available; no assets will be deleted')
for module in ('verl', 'harbor', 'verl_patch', 'harbor_patch'):
    location=pathlib.Path(importlib.util.find_spec(module).origin).resolve()
    if not location.is_relative_to(r): raise RuntimeError(f'Wrong source for {module}: {location}')
    print(module,location,flush=True)
memory=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True)
if len(memory.splitlines()) != 8: raise RuntimeError('Exactly eight GPUs required')
if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True).strip():
    raise RuntimeError('GPU compute processes present; refusing overlap')
if any(int(v)>1000 for v in memory.splitlines()): raise RuntimeError('GPUs occupied; no existing process will be stopped')
for name in ('raylet','gcs_server'):
    if subprocess.run(['pgrep','-x',name],stdout=subprocess.DEVNULL).returncode==0:
        raise RuntimeError('Existing Ray runtime; refusing duplicate launch')
PY
/home/ubuntu/.local/bin/lego-cuda12-run bash scripts/train/train.sh "scripts/train/configs/$config" > "$log" 2>&1
