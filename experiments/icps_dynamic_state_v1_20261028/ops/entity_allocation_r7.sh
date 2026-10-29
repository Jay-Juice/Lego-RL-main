#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/entity_allocation_r7
test ! -e .private_entity_allocation_r7
test ! -e reports/entity_allocation_r7
umask 077
mkdir logs/entity_allocation_r7 .private_entity_allocation_r7 reports/entity_allocation_r7
exec >logs/entity_allocation_r7/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/entity_allocation_r7/exit' EXIT
sha256sum -c validation/ENTITY_ALLOCATION_R7.sha256
export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
"$PY" -B validation/entity_allocation_r7_contracts.py >logs/entity_allocation_r7/contracts.log 2>&1
printf 'generate_label_denied_four_shards\n' >logs/entity_allocation_r7/state
pids=()
for i in 0 1 2 3; do
  "$PY" -B validation/entity_allocation_r7.py generate "$i" >"logs/entity_allocation_r7/generation_$i.log" 2>&1 &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
test "$failed" -eq 0
"$PY" -B validation/entity_allocation_r7.py combine
printf 'score_frozen_development_outputs\n' >logs/entity_allocation_r7/state
"$PY" -B validation/entity_allocation_r7.py score >logs/entity_allocation_r7/score.log 2>&1
"$PY" -B validation/entity_loss_diagnostic_r7.py >logs/entity_allocation_r7/diagnostic.log 2>&1
printf 'complete_development_only\n' >logs/entity_allocation_r7/state
