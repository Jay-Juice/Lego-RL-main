#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
"$PY" -B ops/session_receipt_r6.py check
test ! -e logs/confirmation_r6
mkdir logs/confirmation_r6
exec >logs/confirmation_r6/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/confirmation_r6/exit' EXIT
sha256sum -c validation/CONFIRMATION_R6.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'freeze_exposure_metadata\n' >logs/confirmation_r6/state
"$PY" -B ops/freeze_confirmation_r6.py >logs/confirmation_r6/exposure.log 2>&1
printf 'capture_readonly_W0\n' >logs/confirmation_r6/state
"$PY" -B ops/confirmation_capture_r6.py >logs/confirmation_r6/capture.log 2>&1
printf 'generate_label_denied\n' >logs/confirmation_r6/state
"$PY" -B validation/confirmation_r6.py generate >logs/confirmation_r6/generation.log 2>&1
printf 'score_frozen_outputs\n' >logs/confirmation_r6/state
"$PY" -B validation/confirmation_r6.py score >logs/confirmation_r6/score.log 2>&1
printf 'complete_review_admission\n' >logs/confirmation_r6/state
