#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/development_r5
mkdir logs/development_r5
exec >logs/development_r5/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/development_r5/exit' EXIT
sha256sum -c validation/R5_SOURCE.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'contracts\n' >logs/development_r5/state
"$PY" -B tests/test_guard_windows_r5.py -v >logs/development_r5/contracts.log 2>&1
printf 'generation\n' >logs/development_r5/state
"$PY" -B validation/development_r5.py generate r5 >logs/development_r5/generation.log 2>&1
"$PY" -B validation/development_r5.py control r5 >logs/development_r5/control.log 2>&1
printf 'scoring\n' >logs/development_r5/state
"$PY" -B validation/development_r5.py score r5 >logs/development_r5/score.log 2>&1
printf 'complete_not_training_admission\n' >logs/development_r5/state
