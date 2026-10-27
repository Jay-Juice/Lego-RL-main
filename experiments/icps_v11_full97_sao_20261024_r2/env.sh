#!/bin/bash
set -euo pipefail
export ICPS_FORMAL_ROOT=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_v11_full97_sao_20261024_r2
export ICPS_V11_ROOT=$ICPS_FORMAL_ROOT ICPS_V11_OVERLAY=1
export ICPS_V11_ORIGINAL_SOURCE=$ICPS_FORMAL_ROOT/core
export ICPS_V11_CACHED_IMAGES=$ICPS_FORMAL_ROOT/preflight/FULL6248_PREPARED_IMAGES.json
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONPATH=$ICPS_FORMAL_ROOT/runtime:$ICPS_FORMAL_ROOT/src:$ICPS_FORMAL_ROOT/core:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015/src:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015/third_party/verl:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015/third_party/harbor/src:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015
export GLOO_SOCKET_IFNAME=eno1 TP_SOCKET_IFNAME=eno1 NCCL_SOCKET_IFNAME=eno1
export DOCKER_HOST=unix:///var/run/docker.sock
