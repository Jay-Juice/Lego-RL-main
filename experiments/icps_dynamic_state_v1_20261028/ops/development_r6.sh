#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/development_r6
mkdir logs/development_r6
exec >logs/development_r6/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/development_r6/exit' EXIT
sha256sum -c validation/R6_SOURCE.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'contracts\n' >logs/development_r6/state
"$PY" -B tests/test_rank_windows_r6.py -v >logs/development_r6/contracts.log 2>&1
printf 'generation\n' >logs/development_r6/state
"$PY" -B validation/development_r6.py generate r6 >logs/development_r6/generation.log 2>&1
"$PY" -B validation/development_r6.py control r6 >logs/development_r6/control.log 2>&1
printf 'scoring\n' >logs/development_r6/state
"$PY" -B validation/development_r6.py score r6 >logs/development_r6/score.log 2>&1
printf 'complete_not_training_admission\n' >logs/development_r6/state
