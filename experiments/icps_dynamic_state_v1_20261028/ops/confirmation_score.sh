#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test "$(cat logs/confirmation_capture_r4/exit)" = 0
test ! -e logs/confirmation_score_r4
mkdir logs/confirmation_score_r4
exec >logs/confirmation_score_r4/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/confirmation_score_r4/exit' EXIT
sha256sum -c validation/CONFIRMATION_SCORE.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'scorer_contracts\n' >logs/confirmation_score_r4/state
"$PY" -B tests/test_confirmation_scoring.py -v >logs/confirmation_score_r4/contracts.log 2>&1
printf 'label_denied_generation\n' >logs/confirmation_score_r4/state
"$PY" -B validation/confirmation.py generate >logs/confirmation_score_r4/generation.log 2>&1
printf 'independent_scoring\n' >logs/confirmation_score_r4/state
"$PY" -B validation/confirmation.py score >logs/confirmation_score_r4/score.log 2>&1
printf 'complete_read_admission_result\n' >logs/confirmation_score_r4/state
