#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/development_r2
mkdir -p logs/development_r2 reports
exec >logs/development_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/development_r2/exit' EXIT
sha256sum -c validation/SOURCE_R2.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'cpu_tests\n' >logs/development_r2/state
"$PY" -B tests/test_dense_state.py -v >logs/development_r2/cpu.log 2>&1
printf 'generation\n' >logs/development_r2/state
"$PY" -B validation/development.py generate r2 >logs/development_r2/generation.log 2>&1
printf 'scoring\n' >logs/development_r2/state
"$PY" -B validation/development.py score r2 >logs/development_r2/score.log 2>&1
printf 'complete\n' >logs/development_r2/state
