#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
umask 077
mkdir logs/dynamic_quality_r7_r2
exec >logs/dynamic_quality_r7_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/dynamic_quality_r7_r2/exit' EXIT
sha256sum -c validation/DYNAMIC_QUALITY_R7.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
export PYTHONPATH="$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
"$B/.venv/bin/python" -B validation/dynamic_quality_r7.py
