#!/usr/bin/env python3
"""Create deterministic, disjoint copies of a Harbor task dataset."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--n-shards", type=int, default=8)
    parser.add_argument("--expected-tasks", type=int, default=500)
    parser.add_argument(
        "--include-file",
        type=Path,
        help="optional newline-delimited task names to include from the source dataset",
    )
    args = parser.parse_args()

    if args.n_shards < 1:
        raise SystemExit("--n-shards must be positive")
    source_tasks = sorted(
        path for path in args.source.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    )
    if len(source_tasks) != args.expected_tasks:
        raise SystemExit(
            f"expected {args.expected_tasks} tasks in {args.source}, found {len(source_tasks)}"
        )
    tasks_by_name = {path.name: path for path in source_tasks}
    if args.include_file is not None:
        requested = [
            line.strip()
            for line in args.include_file.read_text().splitlines()
            if line.strip()
        ]
        if not requested:
            raise SystemExit(f"include file is empty: {args.include_file}")
        if len(requested) != len(set(requested)):
            raise SystemExit(f"include file contains duplicate task names: {args.include_file}")
        unknown = sorted(set(requested) - set(tasks_by_name))
        if unknown:
            raise SystemExit(f"include file contains unknown tasks: {unknown[:5]}")
        tasks = [tasks_by_name[name] for name in sorted(requested)]
    else:
        tasks = source_tasks

    assignments = [tasks[index::args.n_shards] for index in range(args.n_shards)]
    args.output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[str]] = {}
    for shard_id, shard_tasks in enumerate(assignments):
        shard_dir = args.output / f"shard_{shard_id}"
        shard_dir.mkdir(exist_ok=True)
        expected_names = {path.name for path in shard_tasks}
        existing_names = {path.name for path in shard_dir.iterdir() if path.is_dir()}
        extras = existing_names - expected_names
        if extras:
            raise SystemExit(f"unexpected tasks in {shard_dir}: {sorted(extras)[:5]}")
        for source_task in shard_tasks:
            target = shard_dir / source_task.name
            if target.exists():
                if not (target / "task.toml").is_file():
                    raise SystemExit(f"incomplete existing task: {target}")
                continue
            shutil.copytree(source_task, target)
        manifest[str(shard_id)] = [path.name for path in shard_tasks]

    flat = [name for names in manifest.values() for name in names]
    if len(flat) != len(set(flat)) or set(flat) != {path.name for path in tasks}:
        raise SystemExit("shards are not an exact, disjoint cover of the source dataset")
    payload = {
        "source": str(args.source.resolve()),
        "source_n_tasks": len(source_tasks),
        "n_tasks": len(tasks),
        "n_shards": args.n_shards,
        "shard_sizes": {key: len(value) for key, value in manifest.items()},
        "assignments": manifest,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(payload["shard_sizes"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
