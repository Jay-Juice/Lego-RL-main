#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/capacity_allocation_r7_score_r2
umask 077
mkdir logs/capacity_allocation_r7_score_r2
exec >logs/capacity_allocation_r7_score_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/capacity_allocation_r7_score_r2/exit' EXIT
sha256sum -c validation/CAPACITY_ALLOCATION_R7.sha256
sha256sum -c validation/CAPACITY_SCORE_R2.sha256
sha256sum -c validation/CAPACITY_LOSS_DIAGNOSTIC_R7.sha256
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1
"$PY" -B validation/capacity_score_r2_contracts.py
"$PY" -B validation/capacity_score_r2.py >logs/capacity_allocation_r7_score_r2/score.log 2>&1
"$PY" -B validation/capacity_loss_diagnostic_r7.py >logs/capacity_allocation_r7_score_r2/diagnostic.log 2>&1
printf 'complete_same_frozen_generation_scored\n' >logs/capacity_allocation_r7_score_r2/state
