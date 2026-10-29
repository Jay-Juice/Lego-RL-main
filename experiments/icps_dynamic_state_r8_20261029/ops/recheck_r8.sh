#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_r8_20261029
cd "$N"
test ! -e logs/recheck_r8
mkdir logs/recheck_r8
exec >logs/recheck_r8/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/recheck_r8/exit' EXIT
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false CUDA_VISIBLE_DEVICES=
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B validation/recheck_r8.py generate
/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -B validation/recheck_r8.py score
