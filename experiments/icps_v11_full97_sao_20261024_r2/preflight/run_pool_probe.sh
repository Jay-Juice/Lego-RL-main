#!/bin/bash
set -euo pipefail
F=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_v11_full97_sao_20261024_r2
R=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
source "$F/env.sh"
export ICPS_FORMAL_RUN_DIR=$("$PY" -B -c 'import json,os;print(json.load(open(os.environ["ICPS_FORMAL_ROOT"]+"/preflight/NAMESPACE.json"))["run"])')
export ICPS_CHECKPOINT_ROOT=$("$PY" -B -c 'import json,os;print(json.load(open(os.environ["ICPS_FORMAL_ROOT"]+"/preflight/NAMESPACE.json"))["checkpoint"])')
export REPO_ROOT="$R" TEMPLATE_ROOT="$R/scripts/templates" TRAIN_LIB_DIR="$R/scripts/train/lib" CONFIG_PATH="$F/ICPS_V11_FULL_LAUNCH_CONFIG.env" DRY_RUN=1
source "$TRAIN_LIB_DIR/runtime.sh"
source_config_and_templates
cd "$R"
/home/ubuntu/.local/bin/lego-cuda12-run "$PY" -B "$F/tests/full_pool_probe.py" > "$F/preflight/full_pool_probe_r1.log" 2>&1
