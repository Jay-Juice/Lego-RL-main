#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
queue="$root/logs/nosave_acceptance_v2_20261015"
mkdir "$queue"
exec >"$queue/supervisor.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" > "$queue/exit"' EXIT
unset FLASH_ATTENTION_DETERMINISTIC PI_DIAGNOSTIC_FULL_HASH PI_DIAGNOSTIC_REQUIRE_REPEAT PI_DIAGNOSTIC_DIR PI_RESUME_MODE
printf 'acceptance %s\n' "$(date -Is)" > "$queue/state"
bash ops/run_phase.sh acceptance_nosave
printf '0\n' > "$queue/acceptance.exit"
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import hashlib,json,pathlib,math,subprocess
r=pathlib.Path.cwd();a=json.loads((r/'logs/nosave_acceptance_v2_20261015/result.json').read_text())
assert a['status']=='passed' and a['production_updates']==0
assert not a['checkpoint_saved'] and not a['checkpoint_loaded'] and a['warmup_checkpoint_steps']==[]
assert a['actor_tensors_unchanged'] and a['pi_records_unchanged'] and a['empty_pi_value_max_abs_diff']<=1e-5
assert a['source_revision']==hashlib.sha256((r/'VERSION_SOURCE_SHA256.json').read_bytes()).hexdigest()
assert not (r/'logs/train_current_launcher.txt').exists(),'Formal training already launched'
for group in ('actor','critic'):assert a[group] and all(math.isfinite(v) for v in a[group].values())
subprocess.run(['/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python','-B','utils/validate_pi_source.py'],check=True)
PY
printf 'waiting_resources %s\n' "$(date -Is)" > "$queue/state"
while ! /media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import pathlib,shutil,subprocess,sys
ok=shutil.disk_usage(pathlib.Path.cwd()).free>=200*1024**3
ok &= not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True).strip()
for p in ('raylet','gcs_server'):ok &= subprocess.run(['pgrep','-x',p],stdout=subprocess.DEVNULL).returncode!=0
sys.exit(0 if ok else 1)
PY
do sleep 30; done
printf 'training %s\n' "$(date -Is)" > "$queue/state"
bash ops/run_phase.sh train
printf 'complete %s\n' "$(date -Is)" > "$queue/state"
