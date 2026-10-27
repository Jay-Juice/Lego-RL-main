#!/bin/bash
set -euo pipefail
echo "BLOCKED: research candidate; admission not complete. Do not launch inherited training." >&2
exit 78
