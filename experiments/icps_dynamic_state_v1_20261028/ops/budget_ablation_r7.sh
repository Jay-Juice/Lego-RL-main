#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/budget_ablation_r7
mkdir logs/budget_ablation_r7
exec >logs/budget_ablation_r7/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/budget_ablation_r7/exit' EXIT
sha256sum -c validation/BUDGET_ABLATION_R7.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
printf 'generate_label_denied\n' >logs/budget_ablation_r7/state
"$PY" -B validation/budget_ablation_r7.py generate >logs/budget_ablation_r7/generation.log 2>&1
printf 'score_frozen_development_outputs\n' >logs/budget_ablation_r7/state
"$PY" -B validation/budget_ablation_r7.py score >logs/budget_ablation_r7/score.log 2>&1
printf 'complete_development_only\n' >logs/budget_ablation_r7/state
