#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_r8_20261029
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
test ! -e logs/harbor_dynamic_r8_r3
mkdir logs/harbor_dynamic_r8_r3
exec >logs/harbor_dynamic_r8_r3/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/harbor_dynamic_r8_r3/exit' EXIT
sha256sum -c validation/R8_PROBE.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export ICPS_V11_ROOT="$N" ICPS_V11_OVERLAY=1
export ICPS_V11_CACHED_IMAGES="$B/experiments/icps_v11_full97_sao_20261024_r2/preflight/FULL6248_PREPARED_IMAGES.json"
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
export PI_ENABLE=1 PI_FORMAT=icps_dynamic_v1 DOCKER_HOST=unix:///var/run/docker.sock
export LEGO_EVAL_SUBNET_POOL=172.16.0.0/20 LEGO_EVAL_SUBNET_PREFIX=29
export TMPDIR="$B/tmp-dynamic-r8-harbor"
mkdir -p "$TMPDIR"
printf 'preflight_then_actual_Harbor_scripted_probe\n' >logs/harbor_dynamic_r8_r3/state
"$B/.venv/bin/python" -B validation/harbor_dynamic_r8.py >logs/harbor_dynamic_r8_r3/probe.log 2>&1
printf 'complete_not_GPU_or_training_admission\n' >logs/harbor_dynamic_r8_r3/state
