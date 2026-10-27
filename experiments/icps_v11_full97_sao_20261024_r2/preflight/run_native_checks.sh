#!/bin/bash
set -euo pipefail
F=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_v11_full97_sao_20261024_r2
R=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
suffix=${ICPS_PREFLIGHT_SUFFIX:-}
source "$F/env.sh"
export ICPS_FORMAL_RUN_DIR=$("$PY" -B -c 'import json,os;print(json.load(open(os.environ["ICPS_FORMAL_ROOT"]+"/preflight/NAMESPACE.json"))["run"])')
export ICPS_CHECKPOINT_ROOT=$("$PY" -B -c 'import json,os;print(json.load(open(os.environ["ICPS_FORMAL_ROOT"]+"/preflight/NAMESPACE.json"))["checkpoint"])')
mkdir -p "$ICPS_FORMAL_RUN_DIR/tmp"
if [[ ! -e /tmp/icpsfull97r2 && ! -L /tmp/icpsfull97r2 ]]; then ln -s "$ICPS_FORMAL_RUN_DIR/tmp" /tmp/icpsfull97r2; fi
[[ $(readlink -f /tmp/icpsfull97r2) == "$ICPS_FORMAL_RUN_DIR/tmp" ]]
cd "$R"
/home/ubuntu/.local/bin/lego-cuda12-run bash scripts/train/train.sh --preflight-only "$F/ICPS_V11_FULL_LAUNCH_CONFIG.env" > "$F/preflight/native_preflight${suffix}.log" 2>&1
/home/ubuntu/.local/bin/lego-cuda12-run bash scripts/train/train.sh --dry-run "$F/ICPS_V11_FULL_LAUNCH_CONFIG.env" > "$F/preflight/dryrun${suffix}.log" 2>&1
export REPO_ROOT="$R" TEMPLATE_ROOT="$R/scripts/templates" TRAIN_LIB_DIR="$R/scripts/train/lib" CONFIG_PATH="$F/ICPS_V11_FULL_LAUNCH_CONFIG.env" DRY_RUN=1
source "$TRAIN_LIB_DIR/runtime.sh"
source "$TRAIN_LIB_DIR/hydra_args.sh"
source_config_and_templates
initialize_runtime > "$F/preflight/resolve_environment${suffix}.log" 2>&1
/home/ubuntu/.local/bin/lego-cuda12-run "$PY" -B "$F/src/resolve_audit.py" > "$F/preflight/parity${suffix}.log" 2>&1
