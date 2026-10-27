#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/development_r3
mkdir -p logs/development_r3 reports
exec >logs/development_r3/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/development_r3/exit' EXIT
sha256sum -c validation/SOURCE_R3.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'cpu_tests\n' >logs/development_r3/state
"$PY" -B tests/test_dense_state.py -v >logs/development_r3/cpu.log 2>&1
printf 'generation\n' >logs/development_r3/state
"$PY" -B validation/development.py generate r3 >logs/development_r3/generation.log 2>&1
printf 'scoring\n' >logs/development_r3/state
"$PY" -B validation/development.py score r3 >logs/development_r3/score.log 2>&1
"$PY" -B tests/test_dense_real.py r3 >logs/development_r3/real_contracts.log 2>&1
"$PY" -B ops/dynamic_constructed_r3.py >logs/development_r3/dynamic_constructed.log 2>&1
printf 'complete\n' >logs/development_r3/state
