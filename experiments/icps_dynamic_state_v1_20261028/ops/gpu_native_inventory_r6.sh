#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
test ! -e logs/gpu_native_inventory_r6
mkdir logs/gpu_native_inventory_r6
exec >logs/gpu_native_inventory_r6/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_native_inventory_r6/exit' EXIT
sha256sum -c validation/GPU_NATIVE_INVENTORY_R6.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export ICPS_V11_ROOT="$N" ICPS_V11_OVERLAY=1
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
printf 'CPU_import_and_readonly_source_inventory\n' >logs/gpu_native_inventory_r6/state
/home/ubuntu/.local/bin/lego-cuda12-run "$B/.venv/bin/python" -B validation/gpu_native_inventory_r6.py
printf 'complete_inventory_review_pending_no_launch\n' >logs/gpu_native_inventory_r6/state
