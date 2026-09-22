#!/usr/bin/env bash
# Build one portable offline grader image for all SWE-bench Verified tasks.
#
# The image is extracted once by RemoteDockerEnvironment and mounted read-only
# at /opt/lego-verifier in every task container. Task images therefore need no
# uv installation, PyPI access, or duplicated verifier package layers.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SWEBENCH_VERSION="${SWEBENCH_VERSION:-4.0.3}"
OUT="${OUT:-$REPO_ROOT/data/verifier-runtime-$SWEBENCH_VERSION}"
IMAGE_TAG="${IMAGE_TAG:-lego-rl/swebench-verifier-runtime:${SWEBENCH_VERSION}-py311}"

SWEBENCH_SPEC="swebench==$SWEBENCH_VERSION" \
    OUT="$OUT" \
    bash "$REPO_ROOT/utils/build_grading_toolchain_v2.sh"

docker build \
    --build-arg "SWEBENCH_VERSION=$SWEBENCH_VERSION" \
    --tag "$IMAGE_TAG" \
    --file "$REPO_ROOT/utils/verifier_runtime/Dockerfile" \
    "$OUT"

docker run --rm "$IMAGE_TAG" \
    /opt/lego-verifier/python311/bin/python3 -c \
    'import datasets, fastcore, swebench; print("offline verifier image OK")'

printf 'Built %s\n' "$IMAGE_TAG"
printf 'Configure Docker Harbor with:\n'
printf '  HARBOR_VERIFIER_RUNTIME_IMAGE=%s\n' "$IMAGE_TAG"
