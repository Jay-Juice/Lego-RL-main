#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
cd "$N"
test ! -e logs/gpu_offline_assets_r6_contracts_r2
mkdir logs/gpu_offline_assets_r6_contracts_r2
exec >logs/gpu_offline_assets_r6_contracts_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_offline_assets_r6_contracts_r2/exit' EXIT
sha256sum -c validation/GPU_OFFLINE_ASSETS_R6_CONTRACTS.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'CPU_contracts_and_readonly_asset_hashing\n' >logs/gpu_offline_assets_r6_contracts_r2/state
"$B/.venv/bin/python" -B validation/gpu_offline_assets_r6_contracts.py --actual-assets
printf 'complete_offline_assets_only_no_launch\n' >logs/gpu_offline_assets_r6_contracts_r2/state
