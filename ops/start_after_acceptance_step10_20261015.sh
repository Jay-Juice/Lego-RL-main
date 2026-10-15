#!/usr/bin/env bash
# Follow-up gate for the user's save5 cancellation during running acceptance.
# No model Python changes and no second validation/GPU job are launched here.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
queue="$root/logs/formal_after_step10_change_20261015"
mkdir "$queue"
exec >"$queue/supervisor.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" > "$queue/exit"' EXIT
printf 'waiting_acceptance %s\n' "$(date -Is)" > "$queue/state"
while [ ! -f logs/acceptance_v2_20261015/exit ]; do sleep 15; done
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import hashlib,json,pathlib,subprocess
r=pathlib.Path.cwd(); q=r/'logs/acceptance_v2_20261015'
assert (q/'acceptance.exit').read_text().strip()=='0'
assert (q/'exit').read_text().strip()=='1'  # old source gate correctly refuses change
j=json.loads((q/'result.json').read_text())
assert j['status']=='passed' and j['production_optimizer_updates']==0
assert j['source_revision']=='bbc5d68c0312eeb3806b1f48475f61bbe5df8762076bdf26a7e97f10d7127ee5'
m=r/'VERSION_SOURCE_SHA256.json'
assert hashlib.sha256(m.read_bytes()).hexdigest()=='33e4701e259c2db118ed9df84049c87e2c97d0d699d47d3ed3a5a87da47b8545'
now=json.loads(m.read_text())
# Reconstruct the precise validated manifest: only the future save schedule differs.
key='scripts/train/configs/sao_b64_pi_repair_state_v2_20261015.env'
s=(r/key).read_text(); assert 'PI_WARMUP_CHECKPOINT_STEPS=10\n' in s
old=s.replace('PI_WARMUP_CHECKPOINT_STEPS=10\n','PI_WARMUP_CHECKPOINT_STEPS=5,10\n')
now[key]=hashlib.sha256(old.encode()).hexdigest()
assert hashlib.sha256((json.dumps(now,indent=2)+'\n').encode()).hexdigest()==j['source_revision']
subprocess.run(['/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python','-B','utils/validate_pi_source.py'],check=True)
assert not (r/'logs/train_current_launcher.txt').exists(), 'Formal training already launched'
print('Acceptance passed; sole config delta is user-authorized step5 removal',flush=True)
PY
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
