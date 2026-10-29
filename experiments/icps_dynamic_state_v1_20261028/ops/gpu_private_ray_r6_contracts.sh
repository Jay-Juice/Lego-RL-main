#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
cd "$N"
test ! -e logs/gpu_private_ray_r6_contracts_r2
mkdir logs/gpu_private_ray_r6_contracts_r2
exec >logs/gpu_private_ray_r6_contracts_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_private_ray_r6_contracts_r2/exit' EXIT
sha256sum -c validation/GPU_PRIVATE_RAY_R6_CONTRACTS.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'CPU_lease_and_owned_child_only_no_Ray\n' >logs/gpu_private_ray_r6_contracts_r2/state
"$B/.venv/bin/python" -B validation/gpu_private_ray_r6_contracts.py
printf 'complete_CPU_only_actual_Ray_lifecycle_pending\n' >logs/gpu_private_ray_r6_contracts_r2/state
