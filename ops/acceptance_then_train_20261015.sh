#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
queue="$root/logs/acceptance_v2_20261015"
mkdir "$queue"
exec >"$queue/supervisor.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" > "$queue/exit"' EXIT
printf 'acceptance %s\n' "$(date -Is)" > "$queue/state"
bash ops/run_phase.sh acceptance
printf '0\n' > "$queue/acceptance.exit"
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import hashlib,json,pathlib
r=pathlib.Path.cwd()
j=json.loads((r/'logs/acceptance_v2_20261015/result.json').read_text())
assert j['status']=='passed' and j['production_optimizer_updates']==0
assert j['source_revision']==hashlib.sha256((r/'VERSION_SOURCE_SHA256.json').read_bytes()).hexdigest()
PY
# Retain acceptance checkpoints. Wait for the existing safety floor; never delete
# experiments to make room and never change save frequency.
printf 'waiting_resources %s\n' "$(date -Is)" > "$queue/state"
while ! /media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import pathlib,shutil,subprocess,sys
ok=shutil.disk_usage(pathlib.Path.cwd()).free >= 200*1024**3
ok &= not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True).strip()
for p in ('raylet','gcs_server'):
    ok &= subprocess.run(['pgrep','-x',p],stdout=subprocess.DEVNULL).returncode != 0
sys.exit(0 if ok else 1)
PY
do sleep 30; done
printf 'training %s\n' "$(date -Is)" > "$queue/state"
bash ops/run_phase.sh train
printf 'complete %s\n' "$(date -Is)" > "$queue/state"
