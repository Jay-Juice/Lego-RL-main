#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
CONFIG="$REPO_ROOT/scripts/eval/configs/qwen35_verified_explicit_network.env"
SOURCE_DATA="$REPO_ROOT/data/swebench-verified"
SHARDS_ROOT="${VERIFIED_SHARDS_ROOT:-$REPO_ROOT/data/swebench-verified-shards-8}"
INCLUDE_FILE="${VERIFIED_INCLUDE_FILE:-}"
JOBS_ROOT="$REPO_ROOT/harbor_trials"
RUN_ID="${FULL_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
RUN_DIR="$REPO_ROOT/logs/eval-qwen35-9b-verified-full/$RUN_ID"
WRAPPER=/home/ubuntu/.local/bin/lego-cuda12-run

mkdir -p "$RUN_DIR"
prepare_args=(
    "$SOURCE_DATA" "$SHARDS_ROOT" --n-shards 8 --expected-tasks 500
)
if [ -n "$INCLUDE_FILE" ]; then
    prepare_args+=(--include-file "$INCLUDE_FILE")
fi
"$PYTHON_BIN" "$REPO_ROOT/utils/prepare_verified_shards.py" "${prepare_args[@]}" \
    | tee "$RUN_DIR/shard_manifest.log"

gpu_count=$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)
[ "$gpu_count" -eq 8 ] || { echo "[FATAL] expected 8 GPUs, found $gpu_count" >&2; exit 1; }
if nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q '[0-9]'; then
    echo "[FATAL] GPU compute processes are already running" >&2
    exit 1
fi

echo "$RUN_ID" > "$RUN_DIR/run_id.txt"
pids=()
for shard_id in $(seq 0 7); do
    log="$RUN_DIR/shard_${shard_id}.launcher.log"
    (
        set +e
        CUDA_VISIBLE_DEVICES="$shard_id" \
        SHARD_ID="$shard_id" \
        FULL_RUN_ID="$RUN_ID" \
        VERIFIED_SHARDS_ROOT="$SHARDS_ROOT" \
        N_CONCURRENT="${N_CONCURRENT_PER_GPU:-8}" \
        "$WRAPPER" bash "$REPO_ROOT/scripts/eval/eval.sh" "$CONFIG" \
            > "$log" 2>&1
        code=$?
        echo "$code" > "$RUN_DIR/shard_${shard_id}.exit_code"
        exit "$code"
    ) &
    pids+=("$!")
    echo "[launch] shard=$shard_id gpu=$shard_id pid=${pids[-1]} log=$log"
done

failed=0
for shard_id in $(seq 0 7); do
    if ! wait "${pids[$shard_id]}"; then
        failed=1
        echo "[error] shard $shard_id exited nonzero" >&2
    fi
done

summary="$RUN_DIR/summary.json"
set +e
"$PYTHON_BIN" "$REPO_ROOT/utils/summarize_verified_shards.py" \
    --jobs-root "$JOBS_ROOT" \
    --shards-root "$SHARDS_ROOT" \
    --run-id "$RUN_ID" \
    --output "$summary" \
    | tee "$RUN_DIR/summary.log"
summary_code=${PIPESTATUS[0]}
set -e

if [ "$failed" -ne 0 ] || [ "$summary_code" -ne 0 ]; then
    echo "[DONE WITH ERRORS] run_id=$RUN_ID summary=$summary" >&2
    exit 1
fi
echo "[DONE] run_id=$RUN_ID summary=$summary"
