#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
cd "$N"
test ! -e logs/gpu_launch_gate_r6_contracts
mkdir logs/gpu_launch_gate_r6_contracts
exec >logs/gpu_launch_gate_r6_contracts/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_launch_gate_r6_contracts/exit' EXIT
sha256sum -c validation/GPU_LAUNCH_GATE_R6_CONTRACTS.sha256
export PYTHONDONTWRITEBYTECODE=1
printf 'CPU_receipt_negative_contracts_no_launch\n' >logs/gpu_launch_gate_r6_contracts/state
"$B/.venv/bin/python" -B validation/gpu_launch_gate_r6_contracts.py
printf 'complete_consumer_CPU_only_launcher_pending\n' >logs/gpu_launch_gate_r6_contracts/state
