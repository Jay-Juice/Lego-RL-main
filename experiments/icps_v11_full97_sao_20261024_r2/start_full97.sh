#!/bin/bash
# Single attempt only: no restart/fresh fallback and no step20 watcher.
set -euo pipefail
umask 077
F=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_v11_full97_sao_20261024_r2
R=/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015
PY=/media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python
source "$F/env.sh"
export ICPS_FORMAL_RUN_DIR=$("$PY" -B -c 'import json,os;print(json.load(open(os.environ["ICPS_FORMAL_ROOT"]+"/preflight/NAMESPACE.json"))["run"])')
export ICPS_CHECKPOINT_ROOT=$("$PY" -B -c 'import json,os;print(json.load(open(os.environ["ICPS_FORMAL_ROOT"]+"/preflight/NAMESPACE.json"))["checkpoint"])')
exec 8>"$F/preflight/full97_launch.lock"
flock -n 8 || { echo 'already launched'; exit 1; }
[[ ! -e "$ICPS_FORMAL_RUN_DIR/started.json" && ! -e "$ICPS_FORMAL_RUN_DIR/resolved_actual.json" && ! -e "$ICPS_CHECKPOINT_ROOT" ]]
cd "$F"
sha256sum -c DEPLOYMENT.sha256 > "$ICPS_FORMAL_RUN_DIR/launch_source_check.log"
"$PY" -B -c 'import json,os;from pathlib import Path;from prepare_full import resources;p=Path(os.environ["ICPS_FORMAL_ROOT"]);r=json.loads((p/"LAUNCH_PREFLIGHT.json").read_text());assert r["status"]=="PASSED_FULL97_CONTINUOUS";a=resources();assert a["free_bytes"]>=r["minimum_before_start_bytes"]'
[[ $(readlink -f /tmp/icpsfull97r2) == "$ICPS_FORMAL_RUN_DIR/tmp" ]]
export PI_SOURCE_REVISION=$(sha256sum "$F/DEPLOYMENT.sha256" | cut -d' ' -f1)
"$PY" -B -c 'import json,os,time;from pathlib import Path;p=Path(os.environ["ICPS_FORMAL_RUN_DIR"]);h=(p/"started.json").open("x");json.dump(dict(time=time.strftime("%Y-%m-%d %H:%M:%S %z"),supervisor_pid=os.getppid(),source_manifest=os.environ["PI_SOURCE_REVISION"],full_horizon=97,manual_pause_at20=False),h)'
echo prelaunch_passed > "$ICPS_FORMAL_RUN_DIR/state"
on_exit() { status=$?; trap - EXIT; echo "$status" > "$ICPS_FORMAL_RUN_DIR/exit"; if [[ $status == 0 && -e "$ICPS_FORMAL_RUN_DIR/DRIVER_COMPLETED.json" ]]; then echo completed97 > "$ICPS_FORMAL_RUN_DIR/state"; else echo failed_no_automatic_restart > "$ICPS_FORMAL_RUN_DIR/state"; fi; exit "$status"; }
trap on_exit EXIT
echo training > "$ICPS_FORMAL_RUN_DIR/state"
cd "$R"
/home/ubuntu/.local/bin/lego-cuda12-run bash scripts/train/train.sh "$F/ICPS_V11_FULL_LAUNCH_CONFIG.env" > "$ICPS_FORMAL_RUN_DIR/launcher.log" 2>&1
[[ -e "$ICPS_FORMAL_RUN_DIR/DRIVER_COMPLETED.json" ]]
