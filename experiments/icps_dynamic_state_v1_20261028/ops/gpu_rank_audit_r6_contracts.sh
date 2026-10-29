#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
test ! -e logs/gpu_rank_audit_r6_contracts
mkdir logs/gpu_rank_audit_r6_contracts
exec >logs/gpu_rank_audit_r6_contracts/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_rank_audit_r6_contracts/exit' EXIT
sha256sum -c validation/GPU_RANK_AUDIT_R6_CONTRACTS.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
export ICPS_V11_ROOT="$N" ICPS_V11_OVERLAY=1
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
printf 'CPU_native_API_and_rank_assertions_only\n' >logs/gpu_rank_audit_r6_contracts/state
"$B/.venv/bin/python" -B validation/gpu_rank_audit_r6_contracts.py
printf 'complete_CPU_only_no_real_rank_acceptance\n' >logs/gpu_rank_audit_r6_contracts/state
