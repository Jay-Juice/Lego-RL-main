#!/usr/bin/env python3
"""Merge reward artifacts from complementary sharded Verified runs."""

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
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--run-id", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    expected = {
        path.name
        for path in args.dataset_root.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    }
    rewards: dict[str, float] = {}
    duplicates: list[str] = []
    unexpected: list[str] = []
    invalid_reward_files: list[str] = []
    errors_by_run: dict[str, int] = {}
    scored_by_run: dict[str, int] = {}
    result_files_by_run: dict[str, list[str]] = {}
    started: list[datetime] = []
    finished: list[datetime] = []

    for run_id in args.run_id:
        run_rewards: set[str] = set()
        run_errors = 0
        result_files: list[str] = []
        for shard_id in range(8):
            job_dir = args.jobs_root / (
                f"eval-qwen35-9b-verified-full-{run_id}-s{shard_id}"
            )
            result_path = job_dir / "result.json"
            if result_path.is_file():
                result = json.loads(result_path.read_text())
                result_files.append(str(result_path))
                run_errors += int(result.get("stats", {}).get("n_errors", 0))
                if value := parse_time(result.get("started_at")):
                    started.append(value)
                if value := parse_time(result.get("finished_at")):
                    finished.append(value)
            if not job_dir.is_dir():
                continue
            for reward_path in job_dir.glob("*/verifier/reward.txt"):
                instance_id = reward_path.parents[1].name.rsplit("__", 1)[0]
                try:
                    reward = float(reward_path.read_text().strip())
                except ValueError:
                    invalid_reward_files.append(str(reward_path))
                    continue
                if not math.isfinite(reward) or reward not in (0.0, 1.0):
                    invalid_reward_files.append(str(reward_path))
                    continue
                if instance_id in rewards:
                    duplicates.append(instance_id)
                rewards[instance_id] = reward
                run_rewards.add(instance_id)
        errors_by_run[run_id] = run_errors
        scored_by_run[run_id] = len(run_rewards)
        result_files_by_run[run_id] = result_files

    unexpected = sorted(set(rewards) - expected)
    missing = sorted(expected - set(rewards))
    reward_counts = Counter(str(value) for value in rewards.values())
    solved = sum(value == 1.0 for value in rewards.values())
    summary = {
        "run_ids": args.run_id,
        "expected_tasks": len(expected),
        "scored_unique": len(rewards),
        "solved": solved,
        "score": solved / len(expected) if expected else None,
        "reward_counts": dict(sorted(reward_counts.items())),
        "errors_by_run": errors_by_run,
        "scored_by_run": scored_by_run,
        "missing_tasks": missing,
        "unexpected_tasks": unexpected,
        "invalid_reward_files": invalid_reward_files,
        "duplicate_instances": sorted(set(duplicates)),
        "started_at": min(started).isoformat() if started else None,
        "finished_at": max(finished).isoformat() if finished else None,
        "duration_seconds": (
            (max(finished) - min(started)).total_seconds()
            if started and finished
            else None
        ),
        "result_files_by_run": result_files_by_run,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    complete = not (missing or unexpected or duplicates or invalid_reward_files) and len(expected) == 500
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
