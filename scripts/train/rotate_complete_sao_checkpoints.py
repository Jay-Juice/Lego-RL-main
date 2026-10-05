#!/usr/bin/env python3
"""Keep the newest complete checkpoints for the one SAO experiment.

verl tracks retention in memory, so a resumed process does not count earlier
checkpoints. Run this after the latest checkpoint has completed; it does not
touch the current or either previous complete checkpoint while training runs.
The default is a read-only preview; --apply removes only verified old step dirs.
"""

import argparse
import json
import re
import shutil
from pathlib import Path


EXPERIMENT = "sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1"
STEP_RE = re.compile(r"global_step_(\d+)")


def deletion_plan(root, steps, keep):
    """Keep pending/pinned models; age alone never authorizes deletion."""
    policy_path = root / "checkpoint_retention.json"
    if not policy_path.is_file() or policy_path.is_symlink():
        return [], [n for n, _ in steps[:-keep]]
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("version") != 1:
        raise ValueError("Invalid checkpoint retention policy version")
    sets = {}
    for key in ("protected_steps", "deletion_approved_steps"):
        values = policy.get(key)
        if not isinstance(values, list) or any(type(n) is not int or n < 0 for n in values):
            raise ValueError(f"Invalid retention policy field: {key}")
        sets[key] = set(values)
    remove, blocked = [], []
    for n, path in steps[:-keep]:
        if n in sets["protected_steps"]:
            continue
        if n not in sets["deletion_approved_steps"]:
            blocked.append(n)
        else:
            remove.append((n, path))
    return remove, blocked


def check_complete(step_dir: Path) -> None:
    if step_dir.is_symlink():
        raise ValueError(f"refusing symlink: {step_dir}")
    if not (step_dir / "data.pt").is_file() or (step_dir / "data.pt").stat().st_size == 0:
        raise ValueError(f"missing dataloader state: {step_dir}")
    for role in ("actor", "critic"):
        for kind in ("model", "optim", "extra_state"):
            for rank in range(8):
                path = step_dir / role / f"{kind}_world_size_8_rank_{rank}.pt"
                if not path.is_file() or path.stat().st_size == 0:
                    raise ValueError(f"missing or empty checkpoint shard: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expect-latest", type=int, required=True)
    parser.add_argument("--keep", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="remove old step dirs")
    args = parser.parse_args()
    if args.keep < 2:
        parser.error("--keep must be at least 2")

    root = args.root.resolve(strict=True)
    if args.root.is_symlink() or root.name != EXPERIMENT or root.parent.name != "sao-qwen35-9b-swesmith":
        raise ValueError(f"refusing unexpected checkpoint root: {root}")
    marker = root / "latest_checkpointed_iteration.txt"
    latest = int(marker.read_text().strip())
    if latest != args.expect_latest:
        raise ValueError(f"latest marker is {latest}, expected {args.expect_latest}")

    steps = []
    for path in root.iterdir():
        match = STEP_RE.fullmatch(path.name)
        if match:
            if path.is_symlink() or not path.is_dir() or path.resolve().parent != root:
                raise ValueError(f"refusing unexpected step path: {path}")
            steps.append((int(match.group(1)), path))
    steps.sort()
    if not steps or steps[-1][0] != latest:
        raise ValueError("latest checkpoint directory does not match marker")

    for _, path in steps:
        check_complete(path)
    remove, blocked = deletion_plan(root, steps, args.keep)
    print(f"checkpoint root: {root}")
    print(f"complete steps: {[step for step, _ in steps]}")
    print(f"keep latest {args.keep}: {[step for step, _ in steps[-args.keep:]]}")
    print(f"remove: {[step for step, _ in remove]}")
    print(f"awaiting explicit deletion approval: {blocked}")
    if args.apply:
        if blocked:
            raise ValueError("Refusing deletion: pending checkpoints lack explicit approval")
        for _, path in remove:
            # The explicit marker check above and fixed root constrain deletion.
            shutil.rmtree(path)
            print(f"removed {path}")


if __name__ == "__main__":
    main()
