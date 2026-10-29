#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
cd "$N"
test ! -e logs/confirmation_capture_r4
mkdir -p logs/confirmation_capture_r4
exec >logs/confirmation_capture_r4/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/confirmation_capture_r4/exit' EXIT
sha256sum -c validation/CONFIRMATION_CAPTURE.sha256
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'capture_readonly_W0\n' >logs/confirmation_capture_r4/state
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B ops/confirmation_capture.py >logs/confirmation_capture_r4/capture.log 2>&1
printf 'complete_check_status_counts\n' >logs/confirmation_capture_r4/state
