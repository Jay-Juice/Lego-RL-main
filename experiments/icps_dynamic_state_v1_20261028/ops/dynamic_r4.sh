#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/dynamic_r4
mkdir logs/dynamic_r4
exec >logs/dynamic_r4/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/dynamic_r4/exit' EXIT
sha256sum -c validation/DYNAMIC_R4.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'running_two_CPU_contracts\n' >logs/dynamic_r4/state
"$PY" -B ops/dynamic_constructed_r4.py body_expand >logs/dynamic_r4/body_expand.log 2>&1 &
body_pid=$!
"$PY" -B ops/dynamic_constructed_r4.py flow_expand >logs/dynamic_r4/flow_expand.log 2>&1 &
flow_pid=$!
body_code=0; flow_code=0
wait "$body_pid" || body_code=$?
wait "$flow_pid" || flow_code=$?
printf '%s\n' "$body_code" >logs/dynamic_r4/body_expand.exit
printf '%s\n' "$flow_code" >logs/dynamic_r4/flow_expand.exit
test "$body_code" = 0 && test "$flow_code" = 0
printf 'complete\n' >logs/dynamic_r4/state
