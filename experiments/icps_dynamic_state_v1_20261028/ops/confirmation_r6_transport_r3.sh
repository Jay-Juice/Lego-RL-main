#!/usr/bin/env bash
set -euo pipefail
N=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
cd "$N"
test "$(cat logs/confirmation_r6/exit)" = 1
grep -Fq "assert hashlib.sha256(issue.encode()).hexdigest()==row['instruction_SHA']" logs/confirmation_r6/generation.log
test ! -e logs/confirmation_r6/score.log
test "$(cat logs/confirmation_r6_transport_r2/exit)" = 1
grep -Fq "AssertionError: Previously generated payload drift" logs/confirmation_r6_transport_r2/generation.log
test ! -e logs/confirmation_r6_transport_r3
mkdir logs/confirmation_r6_transport_r3
exec >logs/confirmation_r6_transport_r3/supervisor.log 2>&1
trap 'code=$?; printf "%s\n" "$code" >logs/confirmation_r6_transport_r3/exit' EXIT
sha256sum -c validation/CONFIRMATION_R6.sha256
sha256sum -c validation/CONFIRMATION_R6_TRANSPORT_R2.sha256
sha256sum -c validation/CONFIRMATION_R6_TRANSPORT_R3.sha256
"$PY" -B ops/session_receipt_r6.py check
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'transport_contracts\n' >logs/confirmation_r6_transport_r3/state
"$PY" -B -m unittest discover -s tests -p test_instruction_transport.py -v >logs/confirmation_r6_transport_r3/contracts.log 2>&1
"$PY" -B -m unittest discover -s tests -p test_payload_equivalence_r6.py -v >logs/confirmation_r6_transport_r3/payload_contracts.log 2>&1
printf 'generate_label_denied_same_cohort\n' >logs/confirmation_r6_transport_r3/state
"$PY" -B validation/confirmation_r6_transport_r3.py generate >logs/confirmation_r6_transport_r3/generation.log 2>&1
printf 'score_frozen_outputs\n' >logs/confirmation_r6_transport_r3/state
"$PY" -B validation/confirmation_r6_transport_r3.py score >logs/confirmation_r6_transport_r3/score.log 2>&1
printf 'complete_review_admission\n' >logs/confirmation_r6_transport_r3/state
