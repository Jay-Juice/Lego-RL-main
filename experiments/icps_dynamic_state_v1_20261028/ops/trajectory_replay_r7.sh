#!/usr/bin/env bash
set -euo pipefail
B=/media/ubuntu/D1/zsj/Lego-RL-main
N=$B/experiments/icps_dynamic_state_v1_20261028
R=$B/experiments/pi_repair_state_v2_20261015
cd "$N"
umask 077
mkdir logs/trajectory_replay_r7_r2
exec >logs/trajectory_replay_r7_r2/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/trajectory_replay_r7_r2/exit' EXIT
sha256sum -c validation/TRAJECTORY_REPLAY_R7.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
export ICPS_V11_ROOT="$N" ICPS_V11_OVERLAY=1
export PYTHONPATH="$N/runtime:$N/src:$N/core:$R/src:$R/third_party/verl:$R/third_party/harbor/src:$R"
export PI_TOTAL_BUDGET_ENABLE=1 PI_CRITIC_MAX_SEQ_TOKENS=245760 PI_ACTOR_RESERVED_TOKENS=73728
"$B/.venv/bin/python" -B validation/trajectory_replay_r7.py
