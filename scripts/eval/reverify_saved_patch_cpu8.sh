#!/usr/bin/env bash
set -euo pipefail

# Re-run only the SWE-bench verifier for an existing agent patch. The original
# trial remains untouched; results are written to a new output directory.
if [ "$#" -ne 4 ]; then
    echo "usage: $0 TRIAL_DIR TASK_DIR OUTPUT_DIR TASK_IMAGE" >&2
    exit 2
fi

trial_dir=$(realpath "$1")
task_dir=$(realpath "$2")
output_dir=$3
task_image=$4
patch="$trial_dir/artifacts/predict_patch.diff"
runtime=/opt/harbor-agent-runtime-cache/verifier_lego-rl_swebench-verifier-runtime_4.0.3-py311

[ -s "$patch" ] || { echo "missing saved patch: $patch" >&2; exit 1; }
[ -f "$task_dir/tests/test.sh" ] || { echo "missing test script" >&2; exit 1; }
[ -d "$runtime" ] || { echo "missing offline verifier runtime" >&2; exit 1; }
[ ! -e "$output_dir" ] || { echo "refusing to overwrite $output_dir" >&2; exit 1; }
mkdir -p "$output_dir"
output_dir=$(realpath "$output_dir")

set +e
timeout 1800s docker run --rm --network none --cpus 8 --memory 8g \
    --mount "type=bind,src=$task_dir/tests,dst=/tests,readonly" \
    --mount "type=bind,src=$patch,dst=/tmp/model_patch.diff,readonly" \
    --mount "type=bind,src=$runtime,dst=/opt/lego-verifier,readonly" \
    --mount "type=bind,src=$output_dir,dst=/logs" \
    -e HARBOR_VERIFIER_PYTHON=/opt/lego-verifier/python311/bin/python3 \
    -e HARBOR_VERIFIER_PARSER=/opt/lego-verifier/parser_offline_v2.py \
    --workdir /testbed "$task_image" \
    bash -lc 'set -euo pipefail; git apply --check /tmp/model_patch.diff; git apply /tmp/model_patch.diff; bash /tests/test.sh' \
    >"$output_dir/verifier.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$output_dir/exit_code"
echo "verifier_exit=$code output=$output_dir"
exit "$code"
