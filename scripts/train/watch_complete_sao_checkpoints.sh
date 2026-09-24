#!/usr/bin/env bash
# Enforce three complete SAO checkpoints across a resume without stopping training.
set -euo pipefail

if [ "$#" -ne 1 ] || [[ ! "$1" =~ ^[0-9]+\.lego_sao_resume_[a-zA-Z0-9_]+$ ]]; then
    echo "usage: $0 SCREEN_PID.lego_sao_resume_NAME" >&2
    exit 2
fi

session=$1
session_pid=${session%%.*}
repo=/media/ubuntu/D1/zsj/Lego-RL-main
root="$repo/checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1"
marker="$root/latest_checkpointed_iteration.txt"
last_rotated=25
failures=0

while ps -p "$session_pid" -o args= | grep -Fq "lego_sao_resume_"; do
    latest=$(cat "$marker" 2>/dev/null || true)
    if [[ "$latest" =~ ^[0-9]+$ ]] && (( latest >= 30 && latest % 10 == 0 && latest != last_rotated )); then
        if "$repo/.venv/bin/python" "$repo/scripts/train/rotate_complete_sao_checkpoints.py" \
            --root "$root" --expect-latest "$latest" --keep 3 --apply; then
            echo "[$(date '+%F %T %Z')] retained latest three at global step $latest"
            last_rotated=$latest
            failures=0
        else
            failures=$((failures + 1))
            echo "[$(date '+%F %T %Z')] rotation attempt $failures failed at step $latest" >&2
            if (( failures >= 3 )); then
                echo "checkpoint rotation needs investigation; leaving training untouched" >&2
                exit 1
            fi
        fi
    fi
    sleep 60
done
echo "[$(date '+%F %T %Z')] training screen exited; retention watcher exits"
