#!/usr/bin/env bash
# Stop only the named SAO training screen after its target checkpoint is complete.
set -euo pipefail

if [[ $# -ne 2 || ! $1 =~ ^[0-9]+\.lego_sao_resume_[a-zA-Z0-9_]+$ || ! $2 =~ ^[0-9]+$ ]]; then
    echo "usage: $0 SCREEN_PID.lego_sao_resume_NAME GLOBAL_STEP" >&2
    exit 2
fi

session=$1
screen_pid=${session%%.*}
session_name=${session#*.}
target=$2
if (( target < 30 || target % 10 != 0 )); then
    echo "target must be a global checkpoint step 30, 40, 50, ..." >&2
    exit 2
fi

repo=/media/ubuntu/D1/zsj/Lego-RL-main
root="$repo/checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1"
marker="$root/latest_checkpointed_iteration.txt"

screen_alive() {
    ps -p "$screen_pid" -o args= | grep -Fq "$session_name" &&
        screen -ls | grep -Fq "$session"
}

echo "[$(date '+%F %T %Z')] waiting for complete global_step_$target from $session"
while screen_alive; do
    latest=$(cat "$marker" 2>/dev/null || true)
    if [[ $latest =~ ^[0-9]+$ ]]; then
        if (( latest == target )); then
            break
        fi
        if (( latest > target )); then
            echo "marker advanced past target: $latest > $target; refusing to signal" >&2
            exit 1
        fi
    fi
    sleep 2
done

if ! screen_alive; then
    echo "training screen exited before checkpoint completed; no signal sent" >&2
    exit 1
fi

# This read-only validator checks the marker, data.pt, and all 48 nonempty
# Actor/Critic model, optimizer, and extra-state shards before any signal.
"$repo/.venv/bin/python" "$repo/scripts/train/rotate_complete_sao_checkpoints.py" \
    --root "$root" --expect-latest "$target" --keep 3

if ! screen_alive; then
    echo "training screen exited during checkpoint validation; no signal sent" >&2
    exit 1
fi

echo "[$(date '+%F %T %Z')] global_step_$target complete; sending Ctrl-C to $session"
screen -S "$session" -X stuff "$(printf '\003')"
echo "[$(date '+%F %T %Z')] signal sent; inspect scoped Ray cleanup before evaluation"
