#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
cd "$N"
test ! -e logs/gpu_private_ray_r6_live_r2
mkdir logs/gpu_private_ray_r6_live_r2
exec >logs/gpu_private_ray_r6_live_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_private_ray_r6_live_r2/exit' EXIT
sha256sum -c validation/GPU_PRIVATE_RAY_R6_LIVE.sha256
unset RAY_ADDRESS ICPS_R6_GPU_APPROVED_LAUNCH PYTHONPATH
export CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RAY_USAGE_STATS_ENABLED=0
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'actual_private_Ray_zero_GPU_lifecycle\n' >logs/gpu_private_ray_r6_live_r2/state
R=$B/experiments/pi_repair_state_v2_20261015
export PYTHONPATH="$N/src:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
"$B/.venv/bin/python" -B validation/gpu_nested_ray_config_r6_contracts.py
unset PYTHONPATH
"$B/.venv/bin/python" -B validation/gpu_private_ray_r6_live.py
printf 'complete_actual_Ray_lifecycle_zero_GPU\n' >logs/gpu_private_ray_r6_live_r2/state
