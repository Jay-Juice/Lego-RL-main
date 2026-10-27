#!/usr/bin/env bash
set -euo pipefail
P=/media/ubuntu/D1/zsj/Lego-RL-main/diagnostics/icps_frozen_contrast_20261027
cd "$P"
exec /media/ubuntu/D1/zsj/Lego-RL-main/.venv/bin/python -u -B wait_and_run.py
