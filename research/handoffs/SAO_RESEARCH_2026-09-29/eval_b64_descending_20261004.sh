#!/usr/bin/env bash
set -euo pipefail
cd /media/ubuntu/D1/zsj/Lego-RL-main
ROOT=$PWD
QUEUE=${EVAL_QUEUE_ROOT:-$ROOT/logs/b64_verified_descending_v2_20261004}
mkdir -p "$QUEUE"
exec 9>"$QUEUE/queue.lock"
flock -n 9 || exit 90
trap 'code=$?; echo "$code" > "$QUEUE/exit_code"' EXIT
export TMPDIR=/media/ubuntu/D1/zsj/tmp-e64
mkdir -p "$TMPDIR"
export LEGO_EVAL_SUBNET_POOL=172.16.240.0/20
export LEGO_EVAL_SUBNET_PREFIX=29
export N_CONCURRENT_PER_GPU=32
unset VERIFIED_INCLUDE_FILE
for step in ${EVAL_STEPS:-70 60 50 40 30 20}; do
    export FULL_RUN_ID=b64-v6d-step${step}-20261004-v2-n32-threads
    export VERIFIED_MODEL_PATH=$ROOT/merged_models/b64-v6d-step${step}-20261004
    export VERIFIED_SHARDS_ROOT=$ROOT/data/verified-b64-step${step}-20261004
    RUN=$ROOT/logs/eval-qwen35-9b-verified-full/$FULL_RUN_ID
    [ ! -e "$RUN" ] || { echo "Existing run: $RUN; manual audit required"; exit 91; }
    python3 - "$ROOT" <<'PY'
import shutil,sys,subprocess
assert shutil.disk_usage(sys.argv[1]).free > 45*2**30, 'Need >45 GiB before next model/evaluation'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(), 'GPUs occupied'
PY
    echo "step=$step phase=merge" > "$QUEUE/state.txt"
    CK=$ROOT/checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-b64-w32-v6d-20260930/global_step_$step
    python3 - "$CK" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); assert (p/'data.pt').stat().st_size>0
for role in ['actor','critic']:
 for kind in ['model','optim','extra_state']:
  for rank in range(8): assert (p/role/f'{kind}_world_size_8_rank_{rank}.pt').stat().st_size>0
PY
    if [ "$step" -eq 70 ] && [ -d "$VERIFIED_MODEL_PATH" ]; then
        echo 'Reuse immutable step70 merge from failed pre-trial v1; reverify below'
    else
        [ ! -e "$VERIFIED_MODEL_PATH" ] || { echo 'Existing merge target; manual audit required'; exit 92; }
        CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=8 .venv/bin/python utils/merge_qwen35_dense_fsdp_to_hf.py --local_dir "$CK/actor" --target_dir "$VERIFIED_MODEL_PATH" --base_dir "$ROOT/Qwen3.5-9B" > "$QUEUE/step${step}_merge.log" 2>&1
    fi
    CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=8 .venv/bin/python utils/verify_merged_hf_keys.py "$VERIFIED_MODEL_PATH" "$ROOT/Qwen3.5-9B" --check-finite > "$QUEUE/step${step}_verify.log" 2>&1
    echo "step=$step phase=eval run=$FULL_RUN_ID" > "$QUEUE/state.txt"
    set +e
    bash scripts/eval/run_qwen35_verified_threads_8gpu.sh > "$QUEUE/step${step}_eval.log" 2>&1
    code=$?
    set -e
    echo "$code" > "$QUEUE/step${step}_eval_exit_code"
    python3 "$QUEUE/audit.py" "$FULL_RUN_ID"
    [ "$code" -eq 0 ] || exit "$code"
done
echo 'all_complete' > "$QUEUE/state.txt"
