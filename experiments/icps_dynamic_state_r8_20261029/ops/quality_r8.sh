#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_r8_20261029
cd "$N"
umask 077
mkdir -p logs reports
mkdir logs/quality_r8_r3
exec >logs/quality_r8_r3/log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/quality_r8_r3/exit' EXIT
sha256sum -c validation/R8_PROBE.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$N/src:$N/core"
"$B/.venv/bin/python" -B validation/dynamic_quality_r8.py
"$B/.venv/bin/python" -B validation/contracts_r8.py
