"""Real isolated Harbor/Docker cancellation and fixed-patch verifier check."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from harbor.models.task.task import Task
from harbor.models.trial.paths import TrialPaths
from harbor.verifier.verifier import Verifier
from harbor_patch.environments.guarded_verifier_docker import GuardedVerifierDockerEnvironment


async def main():
    task_dir, patch_path, output_dir = map(Path, sys.argv[1:])
    output_dir.mkdir(exist_ok=False, parents=True)
    task = Task(task_dir)
    paths = TrialPaths(output_dir)
    paths.mkdir()
    env = GuardedVerifierDockerEnvironment(
        environment_dir=task.paths.environment_dir,
        environment_name=task.name,
        session_id="lego-verifier-guard-check-" + str(os.getpid()),
        trial_paths=paths, task_env_config=task.config.environment,
        override_cpus=2, override_memory_mb=8192,
        verifier_runtime_image="lego-rl/swebench-verifier-runtime:4.0.3-py311",
        verifier_runtime_mount_path="/opt/lego-verifier",
        verifier_runtime_image_subpath="opt/lego-verifier",
    )
    settings = dict(OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="1",
                    MKL_NUM_THREADS="1", BLIS_NUM_THREADS="1",
                    NUMEXPR_NUM_THREADS="1", LEGO_VERIFIER_PROCESS_GUARD="1")
    report = {"patch_path": str(patch_path.resolve()),
              "patch_sha256": hashlib.sha256(patch_path.read_bytes()).hexdigest()}
    try:
        await env.start(False)
        probe = await env.exec("printf '%s' \"$OMP_NUM_THREADS\"", env=settings)
        assert probe.stdout == "2", probe
        # TERM-resistant grandchild must not survive cancellation of docker exec.
        command = "bash -c 'trap \"\" TERM; echo $$ > /tmp/guard-child.pid; while :; do sleep 1; done' & wait"
        try:
            await asyncio.wait_for(env.exec(command, env=settings), timeout=3)
            raise AssertionError("Expected cancellation")
        except asyncio.TimeoutError:
            pass
        probe = await env.exec("p=$(cat /tmp/guard-child.pid); if [ -e /proc/$p/stat ]; then awk '{print $3}' /proc/$p/stat; else echo gone; fi")
        assert probe.stdout.strip() in {"gone", "Z"}, probe
        report["cancelled_child_state"] = probe.stdout.strip()
        probe = await env.exec("exit 7", env=settings)
        assert probe.return_code == 7, probe
        probe = await env.exec("printf retry-ok", env=settings)
        assert probe.stdout == "retry-ok", probe
        report["exit_code_and_retry_preserved"] = True
        await env.upload_file(patch_path, "/tmp/fixed-model.diff")
        probe = await env.exec("git apply --check /tmp/fixed-model.diff && git apply /tmp/fixed-model.diff", cwd="/testbed")
        assert probe.return_code == 0, probe
        start = time.monotonic()
        result = await asyncio.wait_for(Verifier(task, paths, env, settings).verify(), timeout=180)
        report.update(rewards=result.rewards, elapsed_seconds=time.monotonic()-start)
    finally:
        await env.stop(delete=False)
    (output_dir / "PASS.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


asyncio.run(main())
