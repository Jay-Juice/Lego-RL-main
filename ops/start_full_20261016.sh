#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
queue="$root/logs/full_restart_20261016"
mkdir "$queue"
exec >"$queue/supervisor.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" > "$queue/exit"' EXIT
unset CUDA_VISIBLE_DEVICES FLASH_ATTENTION_DETERMINISTIC PI_DIAGNOSTIC_FULL_HASH PI_DIAGNOSTIC_REQUIRE_REPEAT PI_DIAGNOSTIC_DIR PI_RESUME_MODE
printf 'gates %s\n' "$(date -Is)" > "$queue/state"
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B - <<'PY'
import json,pathlib,subprocess,hashlib
r=pathlib.Path.cwd()
for name in ('cpu','harbor','dryrun'):
    assert (r/f'logs/final_check_20261016/{name}.exit').read_text().strip()=='0',name
trial=json.loads((r/'logs/harbor_repair_state_final_20261016_result.json').read_text())
assert trial.get('exception_info') is None
proof=json.loads((r/'harbor_trials/integration/pi-integration-8c066a378d/agent/pi_probe_result.json').read_text())
assert proof['status']=='passed' and proof['decoded_dict_real_proxy_passed']
assert proof['baseline_guard_reinit_equal'] and proof['closed_request_rejected_without_generation']
assert proof['actual_model'] is False and proof['verifier_run'] is False
prior=json.loads((r/'logs/nosave_acceptance_v2_20261015/result.json').read_text())
assert prior['status']=='passed' and prior['production_updates']==0
assert prior['actor_tensors_unchanged'] and prior['pi_records_unchanged']
assert (r/'logs/train_launcher_20261015-221659.exit').read_text().strip()=='1'
exp='sao-qwen35-9b-b64-pi-repair-state-v2-20261015'
assert not list((r/'checkpoints/sao-qwen35-9b-swesmith'/exp).glob('global_step_*')), 'Existing checkpoint: explicit resume required'
subprocess.run(['/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python','-B','utils/validate_pi_source.py'],check=True)
(r/'logs/full_restart_20261016/launch_evidence.json').write_text(json.dumps({
    'user_authorized':'2026-10-16 final checks then full training',
    'source_revision':hashlib.sha256((r/'VERSION_SOURCE_SHA256.json').read_bytes()).hexdigest(),
    'harbor_trial':'pi-integration-8c066a378d','freshbase':True,
    'no_warmup_saves':True,'prior_numerical_repeatability_unresolved':True},indent=2))
PY
tar -czf "$queue/source_snapshot.tar.gz" --exclude='__pycache__' --exclude='*.pyc' src scripts/train ops/start_full_20261016.sh VERSION_SOURCE_SHA256.json vendor_overrides
sha256sum "$queue/source_snapshot.tar.gz" > "$queue/source_snapshot.sha256"
printf 'training %s\n' "$(date -Is)" > "$queue/state"
bash ops/run_phase.sh train
printf 'complete %s\n' "$(date -Is)" > "$queue/state"
