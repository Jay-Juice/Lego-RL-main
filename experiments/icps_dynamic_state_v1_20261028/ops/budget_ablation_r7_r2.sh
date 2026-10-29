#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/budget_ablation_r7_r2
test ! -e .private_budget_ablation_r7_r2
test ! -e reports/budget_ablation_r7_r2
umask 077
mkdir logs/budget_ablation_r7_r2 .private_budget_ablation_r7_r2 reports/budget_ablation_r7_r2
exec >logs/budget_ablation_r7_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/budget_ablation_r7_r2/exit' EXIT
sha256sum -c validation/BUDGET_ABLATION_R7_R2.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
printf 'generate_label_denied_four_shards\n' >logs/budget_ablation_r7_r2/state
pids=()
for i in 0 1 2 3; do
  "$PY" -B validation/budget_ablation_r7_r2.py generate "$i" >"logs/budget_ablation_r7_r2/generation_$i.log" 2>&1 &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
test "$failed" -eq 0
"$PY" -B validation/budget_ablation_r7_r2.py combine
printf 'score_frozen_development_outputs\n' >logs/budget_ablation_r7_r2/state
"$PY" -B validation/budget_ablation_r7_r2.py score >logs/budget_ablation_r7_r2/score.log 2>&1
printf 'complete_development_only\n' >logs/budget_ablation_r7_r2/state
