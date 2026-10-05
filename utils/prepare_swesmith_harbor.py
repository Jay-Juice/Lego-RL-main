#!/usr/bin/env python3
"""Prepare offline Harbor tasks from the filtered SWE-Smith JSONL split.

The published SWE-Smith images contain a branch per instance.  Its HEAD is the
injected bug with the FAIL_TO_PASS test files removed, HEAD~1 is the injected
bug with tests present, and HEAD~2 is the clean source.  This utility:

* restores only the selected test files into Harbor's verifier-only directory;
* builds a task image at the buggy branch HEAD and removes ``.git`` so the
  agent cannot recover the clean source from history;
* grades exactly the filtered v7 FAIL_TO_PASS/PASS_TO_PASS nodes without
  downloading verifier packages; and
* optionally checks that the buggy baseline scores 0 and the reverse bug patch
  scores 1 before emitting a verl-compatible parquet index.

It intentionally consumes the already-filtered Agent Lightning JSONL rather
than reloading a newer upstream dataset.  This preserves split membership,
test-node normalization, image digests, and recorded exclusions.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

import pandas as pd


INSTANCE_RE = re.compile(r"[A-Za-z0-9_.-]+")
IMAGE_RE = re.compile(r"[a-z0-9./_-]+@sha256:[0-9a-f]{64}")


def is_dedicated_test_path(value: str) -> bool:
    """Conservative boundary: embedded doctests need a different adapter.

    Restoring an entire source module to restore its tests destroys agent fixes.
    Reject ambiguous paths instead of silently treating them as hidden tests.
    Keep this predicate equivalent to the self-contained generated verifier.
    """
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        return False
    name = path.name.lower()
    return (
        any(part.lower() in {"test", "tests"} for part in path.parts[:-1])
        or name.startswith("test_") or name.endswith("_test.py")
        or name in {"test.py", "tests.py", "conftest.py"}
    )


RUN_TESTS = r'''#!/usr/bin/env python3
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

TESTBED = Path("/testbed")
TESTS = Path("/tests")
LOGS = Path("/logs/verifier")


def is_dedicated_test_path(value: str) -> bool:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        return False
    name = path.name.lower()
    return (
        any(part.lower() in {"test", "tests"} for part in path.parts[:-1])
        or name.startswith("test_") or name.endswith("_test.py")
        or name in {"test.py", "tests.py", "conftest.py"}
    )


def restore_dedicated_tests(config):
    expected = {node.split("::", 1)[0] for node in config["FAIL_TO_PASS"] + config["PASS_TO_PASS"]}
    unsafe = sorted(path for path in expected if not is_dedicated_test_path(path))
    if unsafe:
        raise RuntimeError(f"Unsafe test restoration overlaps possible source modules: {unsafe}")
    payload = TESTS / "payload"
    files = []
    # Validate the entire copy plan before touching any task files.
    for source in sorted(payload.rglob("*")):
        if source.is_symlink():
            raise RuntimeError(f"Symlink in verifier payload: {source}")
        if not source.is_file():
            continue
        relative = source.relative_to(payload)
        if relative.as_posix() not in expected:
            raise RuntimeError(f"Unexpected file in verifier payload: {relative}")
        target = TESTBED / relative
        current = target
        while current != TESTBED:
            if current.is_symlink():
                raise RuntimeError(f"Symlink in test restoration target: {current}")
            current = current.parent
        files.append((source, target))
    if {s.relative_to(payload).as_posix() for s, _ in files} != expected:
        raise RuntimeError("Verifier payload is missing selected test files")
    for source, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def junit_verdict(path, exit_code):
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    if not cases or any(case.find("error") is not None for case in cases):
        raise RuntimeError("pytest produced no test cases or a setup/teardown/collection error")
    failures = sum(case.find("failure") is not None for case in cases)
    passed = sum(case.find("failure") is None and case.find("skipped") is None for case in cases)
    if exit_code == 0 and failures == 0 and passed > 0:
        return 1, passed, failures
    if exit_code == 1 and failures > 0:
        return 0, passed, failures
    raise RuntimeError("pytest exit code and executed-test report do not provide a valid verdict")


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    reward_path = LOGS / "reward.txt"
    # A missing verdict is distinct from a tested, incorrect patch. Never leave
    # a stale/default zero that Harbor could interpret as a valid label.
    reward_path.unlink(missing_ok=True)
    status_path = LOGS / "grading_status.json"
    status_path.unlink(missing_ok=True)
    try:
        config = json.loads((TESTS / "config.json").read_text())
        nodes = list(dict.fromkeys(config["FAIL_TO_PASS"] + config["PASS_TO_PASS"]))
        if not config["FAIL_TO_PASS"] or not nodes:
            raise RuntimeError("missing FAIL_TO_PASS nodes")

        restore_dedicated_tests(config)

        python = "/opt/miniconda3/envs/testbed/bin/python"
        report = LOGS / "pytest-report.xml"
        report.unlink(missing_ok=True)
        command = [
            python,
            "-m",
            "pytest",
            "-rA",
            "--color=no",
            "-o",
            "cache_dir=/tmp/lego-smith-pytest-cache",
            "-p",
            "no:snail",
            f"--junitxml={report}",
        ]
        if importlib.util.find_spec("xdist") is not None:
            command += ["-n", "2"]
        else:
            command += ["-p", "no:xdist"]
        if importlib.util.find_spec("pytest_cov") is not None:
            command += ["--no-cov"]
        command += nodes

        env = os.environ.copy()
        env.update(
            {
                "HOME": "/tmp/lego-smith-home",
                "PYTHONPATH": "/testbed",
                "PYTHONDONTWRITEBYTECODE": "1",
                "OMP_NUM_THREADS": "2",
                "OPENBLAS_NUM_THREADS": "2",
                "PATH": str(Path(python).parent) + os.pathsep + env.get("PATH", ""),
            }
        )
        result = subprocess.run(
            command,
            cwd=TESTBED,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
        (LOGS.parent / "test_output.log").write_text(result.stdout, errors="replace")
        sys.stdout.write(result.stdout)
        if result.returncode not in (0, 1):
            raise RuntimeError(f"pytest did not produce a verdict: exit code {result.returncode}")
        reward, passed, failed = junit_verdict(report, result.returncode)
        reward_path.write_text(f"{reward}\n")
        status_path.write_text(json.dumps({"status": "scored", "pytest_exit_code": result.returncode,
                                           "passed": passed, "failed": failed,
                                           "protocol": "dedicated-tests-verdict-v3"}))
        return 0
    except Exception as exc:
        message = f"SWE-Smith verifier error: {type(exc).__name__}: {exc}\n"
        with (LOGS.parent / "test_output.log").open("a") as handle:
            handle.write(message)
        reward_path.unlink(missing_ok=True)
        status_path.write_text(json.dumps({"status": "unresolved", "error_type": type(exc).__name__, "message": str(exc)}))
        sys.stderr.write(message)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


TEST_SH = r'''#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
/opt/miniconda3/envs/testbed/bin/python /tests/run_tests.py
'''


def run(argv: list[str], *, stdout_binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not stdout_binary,
    )


def load_rows(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return rows, hashlib.sha256(raw).hexdigest()


def validate_row(row: dict) -> None:
    iid = row.get("instance_id", "")
    image = row.get("image", "")
    if INSTANCE_RE.fullmatch(iid) is None:
        raise ValueError(f"unsafe instance_id: {iid!r}")
    if IMAGE_RE.fullmatch(image) is None:
        raise ValueError(f"image is not pinned by digest: {image!r}")
    f2p = row.get("FAIL_TO_PASS")
    p2p = row.get("PASS_TO_PASS")
    if row.get("grading_protocol") != "f2p_file" or not isinstance(f2p, list) or not f2p:
        raise ValueError(f"{iid}: expected prepared f2p_file metadata")
    if not isinstance(p2p, list):
        raise ValueError(f"{iid}: PASS_TO_PASS is not a list")
    f2p_files = {node.split("::", 1)[0] for node in f2p}
    for node in f2p + p2p:
        if "::" not in node:
            raise ValueError(f"{iid}: unsupported test node {node!r}")
        path = PurePosixPath(node.split("::", 1)[0])
        if path.is_absolute() or ".." in path.parts or str(path).startswith("-"):
            raise ValueError(f"{iid}: unsafe test path {path}")
        if str(path) not in f2p_files:
            raise ValueError(f"{iid}: P2P node is outside an F2P file: {node}")


def docker_branch_output(row: dict, command: str, *args: str, binary: bool = False) -> bytes | str:
    script = 'cd /testbed && git checkout --quiet "$1" && shift && ' + command
    result = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "/bin/bash",
            row["image"],
            "-c",
            script,
            "_",
            row["instance_id"],
            *args,
        ],
        stdout_binary=binary,
    )
    return result.stdout


def extract_tests(row: dict, destination: Path) -> None:
    paths = sorted({node.split("::", 1)[0] for node in row["FAIL_TO_PASS"] + row["PASS_TO_PASS"]})
    last_error: Exception | None = None
    for attempt in range(1, 4):
        shutil.rmtree(destination, ignore_errors=True)
        try:
            archive = docker_branch_output(
                row,
                # git archive respects export-ignore (e.g. pandas scripts/tests).
                # Read exact tracked blobs instead: exporting is not evidence of
                # whether a selected test exists in the frozen commit.
                '''python -c 'import io,subprocess,sys,tarfile
with tarfile.open(fileobj=sys.stdout.buffer,mode="w|") as tar:
 for path in sys.argv[1:]:
  entry=subprocess.check_output(["git","ls-tree","HEAD~1","--",path]).decode().split()
  if not entry or entry[0] not in ("100644","100755"): raise RuntimeError("not a regular tracked test: "+path)
  data=subprocess.check_output(["git","show","HEAD~1:"+path])
  info=tarfile.TarInfo(path); info.size=len(data); info.mode=int(entry[0][-3:],8)
  tar.addfile(info,io.BytesIO(data))' "$@"''',
                *paths,
                binary=True,
            )
            destination.mkdir(parents=True, exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
                members = tar.getmembers()
                names = {member.name for member in members if member.isfile()}
                if not set(paths).issubset(names):
                    raise RuntimeError(
                        f"{row['instance_id']}: test archive is missing {set(paths) - names}"
                    )
                for member in members:
                    member_path = PurePosixPath(member.name)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise RuntimeError(f"unsafe archive member: {member.name}")
                tar.extractall(destination, members=members, filter="data")
            return
        except (tarfile.ReadError, RuntimeError) as exc:
            last_error = exc
            if attempt < 3:
                print(
                    f"Retrying {row['instance_id']} test archive after attempt {attempt}: {exc}",
                    flush=True,
                )
                time.sleep(0.5 * attempt)
    raise RuntimeError(f"{row['instance_id']}: failed to extract tests after 3 attempts") from last_error


def image_tag(prefix: str, instance_id: str) -> str:
    slug = instance_id.lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9.-]+", "-", slug).strip(".-")
    digest = hashlib.sha256(instance_id.encode()).hexdigest()[:12]
    return f"{prefix.rstrip('/')}/{slug[:90]}-{digest}:latest"


def write_task(row: dict, task_dir: Path, tag: str) -> None:
    unsafe = sorted({node.split("::", 1)[0] for node in row["FAIL_TO_PASS"] + row["PASS_TO_PASS"]
                     if not is_dedicated_test_path(node.split("::", 1)[0])})
    if unsafe:
        raise ValueError(f"{row['instance_id']}: embedded/source tests require separate adaptation: {unsafe}")
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "instruction.md").write_text(row["problem_statement"].strip() + "\n")

    tests = task_dir / "tests"
    extract_tests(row, tests / "payload")
    (tests / "config.json").write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n")
    (tests / "run_tests.py").write_text(RUN_TESTS)
    (tests / "test.sh").write_text(TEST_SH)
    os.chmod(tests / "test.sh", 0o755)
    os.chmod(tests / "run_tests.py", 0o755)

    environment = task_dir / "environment"
    environment.mkdir()
    dockerfile = f'''FROM {row["image"]}
WORKDIR /testbed
RUN git checkout --quiet {row["instance_id"]} \\
 && test "$(git log -1 --format=%s)" = "Remove F2P Tests" \\
 && rm -rf /testbed/.git \\
 && mkdir -p /logs/agent /logs/verifier /artifacts \\
 && chmod 777 /logs/agent /logs/verifier /artifacts
'''
    (environment / "Dockerfile").write_text(dockerfile)

    task_toml = f'''version = "1.0"

[metadata]
benchmark = "SWE-Smith"
instance_id = "{row['instance_id']}"
repository = "{row.get('repo', 'unknown')}"
category = "debugging"
tags = ["debugging", "swe-bench", "swe-smith", "python-full-v7"]
source = "agent-lightning-python-full-v7"

[verifier]
timeout_sec = 600.0
network_mode = "public"

[agent]
timeout_sec = 1800.0
network_mode = "public"

[environment]
docker_image = "{tag}"
network_mode = "public"
build_timeout_sec = 600.0
cpus = 2
memory_mb = 8192
storage_mb = 10240
'''
    (task_dir / "task.toml").write_text(task_toml)


def build_task(task_dir: Path, tag: str) -> None:
    subprocess.run(
        ["docker", "build", "--network", "none", "--tag", tag, str(task_dir / "environment")],
        check=True,
    )


def run_control(task_dir: Path, tag: str, oracle_patch: Path | None) -> int:
    with tempfile.TemporaryDirectory(prefix=".lego-smith-logs-", dir=task_dir.parent) as log_dir:
        argv = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            "2",
            "--memory",
            "8g",
            "-v",
            f"{task_dir / 'tests'}:/tests:ro",
            "-v",
            f"{log_dir}:/logs",
        ]
        if oracle_patch is not None:
            argv += ["-v", f"{oracle_patch}:/oracle.patch:ro"]
        argv += [tag, "/bin/bash", "-lc"]
        if oracle_patch is None:
            argv += ["/tests/test.sh; rc=$?; chmod -R a+rwX /logs; exit $rc"]
        else:
            argv += [
                "git apply /oracle.patch && /tests/test.sh; "
                "rc=$?; chmod -R a+rwX /logs; exit $rc"
            ]
        subprocess.run(argv, check=True)
        reward = Path(log_dir, "verifier", "reward.txt")
        return int(reward.read_text().strip()) if reward.exists() else -1


def validate_controls(row: dict, task_dir: Path, tag: str) -> dict[str, int]:
    baseline = run_control(task_dir, tag, None)
    gold = docker_branch_output(row, "git diff --binary HEAD~1 HEAD~2", binary=True)
    with tempfile.NamedTemporaryFile(prefix=".lego-smith-oracle-", suffix=".patch", dir=task_dir.parent, delete=False) as file:
        file.write(gold)
        oracle_path = Path(file.name)
    try:
        oracle = run_control(task_dir, tag, oracle_path)
    finally:
        oracle_path.unlink(missing_ok=True)
    if baseline != 0 or oracle != 1:
        raise RuntimeError(
            f"{row['instance_id']}: control validation failed (baseline={baseline}, oracle={oracle})"
        )
    return {"baseline_reward": baseline, "oracle_reward": oracle}


def parquet_row(task_dir: Path, row: dict) -> dict:
    return {
        "prompt": [{"role": "user", "content": str(task_dir)}],
        "reward_model": {"style": "rule", "ground_truth": None},
        "extra_info": {
            "harbor_task_path": str(task_dir.resolve()),
            "instance_id": row["instance_id"],
            "data_source": "swesmith-python-full-v7",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--parquet", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--instance-id", action="append")
    selection.add_argument(
        "--all",
        action="store_true",
        help="prepare every row in the JSONL, preserving source order",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="number of tasks to prepare concurrently (default: 1)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse complete task directories and replace incomplete ones",
    )
    parser.add_argument(
        "--skip-failed",
        action="store_true",
        help="record tasks that cannot be represented offline and continue",
    )
    parser.add_argument("--image-prefix", default="lego-rl-swesmith")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--validate-controls", action="store_true")
    args = parser.parse_args()

    rows, source_sha256 = load_rows(args.jsonl)
    by_id = {row["instance_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise RuntimeError("source JSONL contains duplicate instance IDs")
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    selected_ids = [row["instance_id"] for row in rows] if args.all else args.instance_id
    missing = [iid for iid in selected_ids if iid not in by_id]
    if missing:
        raise KeyError(f"instance IDs are absent from {args.jsonl}: {missing}")
    selected_rows = [by_id[iid] for iid in selected_ids]
    for row in selected_rows:
        validate_row(row)
    if args.output_dir.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=args.resume)

    manifest = {
        "source": str(args.jsonl.resolve()),
        "source_sha256": source_sha256,
        "grading_protocol": "f2p_file",
        "tasks": [],
        "excluded": [],
    }

    def is_complete(task_dir: Path) -> bool:
        required = [
            task_dir / "instruction.md",
            task_dir / "task.toml",
            task_dir / "environment" / "Dockerfile",
            task_dir / "tests" / "config.json",
            task_dir / "tests" / "run_tests.py",
            task_dir / "tests" / "test.sh",
        ]
        payload = task_dir / "tests" / "payload"
        return all(path.is_file() for path in required) and payload.is_dir() and any(payload.rglob("*"))

    def prepare(row: dict) -> tuple[dict | None, dict | None, dict | None]:
        iid = row["instance_id"]
        task_dir = args.output_dir / iid
        tag = image_tag(args.image_prefix, iid)
        controls = None
        staging = args.output_dir / f".preparing-{iid}"
        # A protocol mismatch must never enter --skip-failed cleanup: preserve
        # existing historical tasks and require an explicitly new version.
        if task_dir.exists() and args.resume and is_complete(task_dir):
            if (task_dir / "tests/run_tests.py").read_text() != RUN_TESTS:
                raise ValueError("Existing verifier version differs; create a new asset version instead of resume")
        try:
            if task_dir.exists() and args.resume and is_complete(task_dir):
                print(f"Reusing {iid}", flush=True)
            else:
                if task_dir.exists():
                    shutil.rmtree(task_dir)
                shutil.rmtree(staging, ignore_errors=True)
                print(f"Preparing {iid}", flush=True)
                write_task(row, staging, tag)
                if args.build:
                    build_task(staging, tag)
                if args.validate_controls:
                    if not args.build:
                        raise ValueError("--validate-controls requires --build")
                    controls = validate_controls(row, staging, tag)
                (staging / ".prepared").write_text("ok\n")
                staging.replace(task_dir)
        except Exception as exc:
            shutil.rmtree(staging, ignore_errors=True)
            if not args.skip_failed:
                raise
            shutil.rmtree(task_dir, ignore_errors=True)
            error = {
                "instance_id": iid,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            print(f"Skipping {iid}: {type(exc).__name__}: {exc}", flush=True)
            return None, None, error
        manifest_row = {
            "instance_id": iid,
            "source_row_sha256": row.get("source_row_sha256"),
            "base_image": row["image"],
            "task_image": tag,
            "FAIL_TO_PASS": len(row["FAIL_TO_PASS"]),
            "PASS_TO_PASS": len(row["PASS_TO_PASS"]),
            "controls": controls,
        }
        return manifest_row, parquet_row(task_dir, row), None

    try:
        if args.workers == 1:
            prepared = map(prepare, selected_rows)
            results = list(prepared)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                results = list(executor.map(prepare, selected_rows))
    except Exception:
        print(f"Preparation failed; partial output retained at {args.output_dir}", flush=True)
        raise

    manifest["tasks"] = [item[0] for item in results if item[0] is not None]
    manifest["excluded"] = [item[2] for item in results if item[2] is not None]
    index_rows = [item[1] for item in results if item[1] is not None]

    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    args.parquet.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(index_rows).to_parquet(args.parquet, index=False)
    print(
        f"Wrote {len(index_rows)} tasks to {args.parquet}; "
        f"excluded {len(manifest['excluded'])}",
        flush=True,
    )


if __name__ == "__main__":
    main()
