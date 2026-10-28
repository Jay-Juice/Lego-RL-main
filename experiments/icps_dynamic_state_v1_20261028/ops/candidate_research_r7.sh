#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test ! -e logs/candidate_research_r7
test ! -e .private_candidate_research_r7
test ! -e reports/candidate_research_r7
umask 077
mkdir logs/candidate_research_r7 .private_candidate_research_r7 reports/candidate_research_r7
exec >logs/candidate_research_r7/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/candidate_research_r7/exit' EXIT
sha256sum -c validation/CANDIDATE_RESEARCH_R7.sha256
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
"$PY" -B validation/candidate_research_r7_contracts.py >logs/candidate_research_r7/contracts.log 2>&1
printf 'generate_label_denied_four_shards\n' >logs/candidate_research_r7/state
pids=()
for i in 0 1 2 3; do
  "$PY" -B validation/candidate_research_r7.py generate "$i" >"logs/candidate_research_r7/generation_$i.log" 2>&1 &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
test "$failed" -eq 0
"$PY" -B validation/candidate_research_r7.py combine
printf 'score_frozen_development_outputs\n' >logs/candidate_research_r7/state
"$PY" -B validation/candidate_research_r7.py score >logs/candidate_research_r7/score.log 2>&1
printf 'complete_development_only\n' >logs/candidate_research_r7/state
