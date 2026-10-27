#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
test ! -e logs/proxy_lifecycle_r6
mkdir logs/proxy_lifecycle_r6
exec >logs/proxy_lifecycle_r6/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/proxy_lifecycle_r6/exit' EXIT
sha256sum -c validation/PROXY_LIFECYCLE_R6.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export ICPS_V11_ROOT="$N" ICPS_V11_OVERLAY=1
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
export PI_ENABLE=1 PI_FORMAT=icps_dynamic_v1
printf 'actual_proxy_lifecycle_CPU\n' >logs/proxy_lifecycle_r6/state
"$B/.venv/bin/python" -B validation/proxy_lifecycle_r6.py >logs/proxy_lifecycle_r6/probe.log 2>&1
printf 'complete_not_GPU_or_training_admission\n' >logs/proxy_lifecycle_r6/state
