#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/session_r6_r2
mkdir logs/session_r6_r2
exec >logs/session_r6_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/session_r6_r2/exit' EXIT
sha256sum -c validation/SESSION_R6_R2.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'contracts\n' >logs/session_r6_r2/state
"$PY" -B -m unittest discover -s tests -p test_dynamic_session_r6_r2.py -v >logs/session_r6_r2/contracts.log 2>&1
printf 'initial607_then_constructed24\n' >logs/session_r6_r2/state
"$PY" -B validation/session_r6_r2.py >logs/session_r6_r2/validation.log 2>&1
printf 'complete_not_training_admission\n' >logs/session_r6_r2/state
