#!/usr/bin/env python3
"""Make Harbor SWE-bench Verified tasks use the shared offline verifier runtime.

The operation is idempotent. It removes the per-task uv download from each
Dockerfile and replaces the final ``uv run parser.py`` command with an offline
runtime first path. ``uv`` remains a compatibility fallback when it already
exists in a task image.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


MARKER = "# Lego-RL shared offline verifier runtime"
UV_DOCKERFILE_RE = re.compile(
    r"^\s*RUN curl -LsSf https://astral\.sh/uv/0\.7\.13/install\.sh \| sh\s*$",
    re.MULTILINE,
)
UV_RUN_RE = re.compile(
    r"set \+e\n"
    r"export PATH=\"/root/\.local/bin:\$PATH\"\n"
    r"uv run parser\.py \| tee -a \"\$LOG_FILE\"\n"
    r"exit_code=\$\?\n"
    r"set -e"
)

OFFLINE_RUN = r'''set +e
# Lego-RL shared offline verifier runtime
verifier_python="${HARBOR_VERIFIER_PYTHON:-/opt/lego-verifier/python311/bin/python3}"
verifier_parser="${HARBOR_VERIFIER_PARSER:-/opt/lego-verifier/parser_offline_v2.py}"
if [ -x "$verifier_python" ] && [ -r "$verifier_parser" ]; then
  "$verifier_python" "$verifier_parser" | tee -a "$LOG_FILE"
  exit_code=${PIPESTATUS[0]}
else
  exit_code=3
fi

# Compatibility fallback for environments that intentionally provide uv.
if [ "$exit_code" -eq 3 ] && command -v uv >/dev/null 2>&1; then
  export PATH="/root/.local/bin:$PATH"
  uv run parser.py | tee -a "$LOG_FILE"
  exit_code=${PIPESTATUS[0]}
fi
if [ "$exit_code" -eq 3 ]; then
  echo "ERROR: shared SWE-bench verifier runtime is unavailable" | tee -a "$LOG_FILE"
  # Infrastructure failure: do not write reward=0 and mislabel it as a model failure.
  exit 3
fi
set -e'''


def patch_file(path: Path, transform, check: bool) -> bool:
    before = path.read_text()
    after = transform(before)
    if before == after:
        return False
    if not check:
        path.write_text(after)
    return True


def patch_test_script(text: str) -> str:
    if MARKER in text:
        old = (
            'if [ "$exit_code" -eq 3 ]; then\n'
            '  echo "ERROR: shared SWE-bench verifier runtime is unavailable" | tee -a "$LOG_FILE"\n'
            "fi"
        )
        new = (
            'if [ "$exit_code" -eq 3 ]; then\n'
            '  echo "ERROR: shared SWE-bench verifier runtime is unavailable" | tee -a "$LOG_FILE"\n'
            "  # Infrastructure failure: do not write reward=0 and mislabel it as a model failure.\n"
            "  exit 3\n"
            "fi"
        )
        if old in text:
            return text.replace(old, new, 1)
        return text
    updated, count = UV_RUN_RE.subn(OFFLINE_RUN, text, count=1)
    if count != 1:
        raise ValueError("expected exactly one canonical uv parser block")
    return updated


def patch_dockerfile(text: str) -> str:
    updated, count = UV_DOCKERFILE_RE.subn(
        "# The shared verifier runtime supplies Python and SWE-bench; no network install here.",
        text,
        count=1,
    )
    if count != 1 and "shared verifier runtime supplies Python" not in text:
        raise ValueError("expected exactly one canonical uv install line")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--check", action="store_true", help="report pending changes only")
    args = parser.parse_args()

    task_dirs = sorted(p for p in args.dataset.iterdir() if p.is_dir())
    if not task_dirs:
        raise SystemExit(f"no task directories found under {args.dataset}")

    changed_tests = 0
    changed_dockerfiles = 0
    errors: list[str] = []
    for task_dir in task_dirs:
        test_script = task_dir / "tests" / "test.sh"
        dockerfile = task_dir / "environment" / "Dockerfile"
        try:
            changed_tests += patch_file(test_script, patch_test_script, args.check)
            changed_dockerfiles += patch_file(dockerfile, patch_dockerfile, args.check)
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"{task_dir.name}: {exc}")

    mode = "would change" if args.check else "changed"
    print(
        f"{len(task_dirs)} tasks checked; {mode} {changed_tests} test scripts and "
        f"{changed_dockerfiles} Dockerfiles"
    )
    if errors:
        print("errors:")
        print("\n".join(f"  {error}" for error in errors))
        return 1
    return 1 if args.check and (changed_tests or changed_dockerfiles) else 0


if __name__ == "__main__":
    raise SystemExit(main())
