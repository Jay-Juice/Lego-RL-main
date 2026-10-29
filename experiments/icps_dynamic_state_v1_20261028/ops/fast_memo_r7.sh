#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test "$(cat logs/fast_allocation_r7/exit)" = 0
test ! -e logs/fast_memo_r7
test ! -e .private_fast_memo_r7
test ! -e reports/fast_memo_r7
umask 077
mkdir logs/fast_memo_r7 .private_fast_memo_r7 reports/fast_memo_r7
exec >logs/fast_memo_r7/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/fast_memo_r7/exit' EXIT
sha256sum -c validation/FAST_MEMO_R7.sha256
export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
"$PY" -B validation/fast_memo_r7_contracts.py >logs/fast_memo_r7/contracts.log 2>&1
printf 'replay_label_denied_four_shards\n' >logs/fast_memo_r7/state
pids=()
for i in 0 1 2 3; do
  "$PY" -B validation/fast_memo_replay_r7.py generate "$i" >"logs/fast_memo_r7/replay_$i.log" 2>&1 &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
test "$failed" -eq 0
"$PY" -B validation/fast_memo_replay_r7.py combine >logs/fast_memo_r7/aggregate.log 2>&1
printf 'complete_development_only\n' >logs/fast_memo_r7/state
