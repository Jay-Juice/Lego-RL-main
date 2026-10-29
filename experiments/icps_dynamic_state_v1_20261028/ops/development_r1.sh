#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/development_r1
mkdir -p logs/development_r1 reports
exec >logs/development_r1/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/development_r1/exit' EXIT
sha256sum -c validation/SOURCE_R1.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'cpu_tests\n' >logs/development_r1/state
"$PY" -B tests/test_dense_state.py -v >logs/development_r1/cpu.log 2>&1
printf 'generation\n' >logs/development_r1/state
"$PY" -B validation/development.py generate r1 >logs/development_r1/generation.log 2>&1
printf 'scoring\n' >logs/development_r1/state
"$PY" -B validation/development.py score r1 >logs/development_r1/score.log 2>&1
printf 'complete\n' >logs/development_r1/state
