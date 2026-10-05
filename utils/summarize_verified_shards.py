#!/usr/bin/env python3
"""Merge and validate eight Harbor SWE-bench shard results."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-root", type=Path, required=True)
    parser.add_argument("--shards-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    expected = {
        path.name
        for shard in sorted(args.shards_root.glob("shard_*"))
        for path in shard.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    }
    rewards: dict[str, float] = {}
    duplicate_instances: list[str] = []
    result_files: list[str] = []
    missing_shard_results: list[int] = []
    n_errors = 0
    invalid_reward_files: list[str] = []
    started: list[datetime] = []
    finished: list[datetime] = []

    for shard_id in range(8):
        job_dir = args.jobs_root / f"eval-qwen35-9b-verified-full-{args.run_id}-s{shard_id}"
        result_path = job_dir / "result.json"
        if not result_path.is_file():
            missing_shard_results.append(shard_id)
        else:
            result = json.loads(result_path.read_text())
            result_files.append(str(result_path))
            n_errors += int(result.get("stats", {}).get("n_errors", 0))
            if value := parse_time(result.get("started_at")):
                started.append(value)
            if value := parse_time(result.get("finished_at")):
                finished.append(value)
        if not job_dir.is_dir():
            continue
        for reward_path in job_dir.glob("*/verifier/reward.txt"):
            trial_name = reward_path.parents[1].name
            instance_id = trial_name.rsplit("__", 1)[0]
            try:
                reward = float(reward_path.read_text().strip())
            except ValueError:
                invalid_reward_files.append(str(reward_path))
                continue
            if not math.isfinite(reward) or reward not in (0.0, 1.0):
                invalid_reward_files.append(str(reward_path))
                continue
            if instance_id in rewards:
                duplicate_instances.append(instance_id)
            rewards[instance_id] = reward

    unexpected = sorted(set(rewards) - expected)
    missing = sorted(expected - set(rewards))
    reward_counts = Counter(str(value) for value in rewards.values())
    solved = sum(value == 1.0 for value in rewards.values())
    started_at = min(started).isoformat() if started else None
    finished_at = max(finished).isoformat() if finished else None
    duration_seconds = (
        (max(finished) - min(started)).total_seconds() if started and finished else None
    )
    summary = {
        "run_id": args.run_id,
        "expected_tasks": len(expected),
        "scored_unique": len(rewards),
        "solved": solved,
        "score": solved / len(expected) if expected else None,
        "reward_counts": dict(sorted(reward_counts.items())),
        "n_errors_reported": n_errors,
        "invalid_reward_files": invalid_reward_files,
        "missing_tasks": missing,
        "unexpected_tasks": unexpected,
        "duplicate_instances": sorted(set(duplicate_instances)),
        "missing_shard_results": missing_shard_results,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "result_files": result_files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    complete = len(expected) == 500 and not (
        missing or unexpected or duplicate_instances or missing_shard_results or invalid_reward_files
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
