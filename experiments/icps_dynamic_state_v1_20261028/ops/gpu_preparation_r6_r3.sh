#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
test ! -e logs/gpu_preparation_r6_r3
mkdir logs/gpu_preparation_r6_r3
exec >logs/gpu_preparation_r6_r3/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/gpu_preparation_r6_r3/exit' EXIT
sha256sum -c validation/GPU_PREPARATION_R6_R3.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export ICPS_V11_ROOT="$N" ICPS_V11_OVERLAY=1
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
export PI_ENABLE=1 PI_FORMAT=icps_dynamic_v1
export ICPS_FORMAL_ROOT="$N" ICPS_FORMAL_RUN_DIR="$N/runs/gpu_probe_r6_preparation_only"
export ICPS_CHECKPOINT_ROOT="$N/checkpoints/NEVER_SAVE_GPU_PROBE_R6"
printf 'CPU_fixture_source_resource_after_TensorDict_iteration_fix\n' >logs/gpu_preparation_r6_r3/state
"$B/.venv/bin/python" -B validation/gpu_preparation_r6.py >logs/gpu_preparation_r6_r3/contracts_resources.log 2>&1
printf 'complete_CPU_only_not_GPU_or_training_admission\n' >logs/gpu_preparation_r6_r3/state
