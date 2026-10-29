#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_r8_20261029
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
sha256sum -c validation/R8_GPU.sha256
RUN_ID=$($B/.venv/bin/python -B -c 'import secrets; print("gpu-r6-"+secrets.token_hex(8))')
export ICPS_FORMAL_RUN_DIR="$N/runs/$RUN_ID" ICPS_FORMAL_ROOT="$N"
mkdir -p "$N/runs"
mkdir -m 700 "$ICPS_FORMAL_RUN_DIR"
printf '%s\n' "$ICPS_FORMAL_RUN_DIR"
exec >"$ICPS_FORMAL_RUN_DIR/supervisor.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" >"$ICPS_FORMAL_RUN_DIR/exit"' EXIT
export REPO_ROOT="$B" TEMPLATE_ROOT="$B/scripts/templates"
export CONFIG_PATH="$N/ops/GPU_PROBE_R6.env"
export PYTHONPATH="$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
source "$B/scripts/train/lib/runtime.sh"
source_config_and_templates  # Config assignments only; never initialize_runtime or start_ray_cluster.
unset RAY_ADDRESS ICPS_R6_GPU_APPROVED_LAUNCH ICPS_R6_LAUNCH_RECEIPT_SHA
export LEGO_RL_ROOT="$B" SWE_LEGO_RL_ROOT="$B" ICPS_V11_OVERLAY=1 ICPS_V11_ROOT="$N"
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RAY_USAGE_STATS_ENABLED=0
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
export TMPDIR="$ICPS_FORMAL_RUN_DIR/tmp" TRITON_CACHE_DIR="$ICPS_FORMAL_RUN_DIR/cache/triton" TORCHINDUCTOR_CACHE_DIR="$ICPS_FORMAL_RUN_DIR/cache/inductor"
mkdir -p "$TMPDIR" "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR"
/home/ubuntu/.local/bin/lego-cuda12-run "$B/.venv/bin/python" -B -m gpu_launch_r6
