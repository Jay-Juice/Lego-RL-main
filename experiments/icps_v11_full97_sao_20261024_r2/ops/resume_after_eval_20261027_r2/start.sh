#!/bin/bash
set -euo pipefail
umask 077
F=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_v11_full97_sao_20261024_r2
R=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015
O=$F/ops/resume_after_eval_20261027_r2
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
source "$F/env.sh"
export PYTHONPATH="$O:$PYTHONPATH"
export ICPS_FORMAL_RUN_DIR=$F/runs/resume40_after_eval_20261027_r2
export ICPS_CHECKPOINT_ROOT=$F/checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-b64-icps-v11-192-full97-r2-20261024
export ICPS_RESUME_FROM=$ICPS_CHECKPOINT_ROOT/global_step_40
mkdir -p "$ICPS_FORMAL_RUN_DIR"
exec 8>"$ICPS_FORMAL_RUN_DIR/launch.lock"
flock -n 8 || exit 1
[[ ! -e "$ICPS_FORMAL_RUN_DIR/queued" ]]
date -Is > "$ICPS_FORMAL_RUN_DIR/queued"
trap 's=$?; echo "$s" > "$ICPS_FORMAL_RUN_DIR/exit"' EXIT
while true; do
  set +e
  "$PY" -B "$O/gate.py" >> "$ICPS_FORMAL_RUN_DIR/gate.log" 2>&1
  status=$?
  set -e
  if [[ $status == 0 ]]; then break; fi
  if [[ $status != 75 ]]; then echo failed_gate_no_restart > "$ICPS_FORMAL_RUN_DIR/state"; exit "$status"; fi
  sleep 60
done
[[ ! -e /tmp/icpsr40o27r2 && ! -L /tmp/icpsr40o27r2 ]]
mkdir -p "$ICPS_FORMAL_RUN_DIR/tmp"
ln -s "$ICPS_FORMAL_RUN_DIR/tmp" /tmp/icpsr40o27r2
export PI_SOURCE_REVISION=$(sha256sum "$F/DEPLOYMENT.sha256" | cut -d' ' -f1)
tar -czf "$ICPS_FORMAL_RUN_DIR/resume_source_snapshot.tar.gz" -C "$O" .
sha256sum "$ICPS_FORMAL_RUN_DIR/resume_source_snapshot.tar.gz" > "$ICPS_FORMAL_RUN_DIR/resume_source_snapshot.sha256"
date -Is > "$ICPS_FORMAL_RUN_DIR/started"
echo training_resume40 > "$ICPS_FORMAL_RUN_DIR/state"
cd "$R"
/home/ubuntu/.local/bin/lego-cuda12-run bash scripts/train/train.sh "$O/resume.env" > "$ICPS_FORMAL_RUN_DIR/launcher.log" 2>&1
[[ -e "$ICPS_FORMAL_RUN_DIR/DRIVER_COMPLETED.json" ]]
echo completed97 > "$ICPS_FORMAL_RUN_DIR/state"
