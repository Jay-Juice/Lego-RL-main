"""Actual local Ray lifecycle canary, zero GPUs, no model or training imports.

This closes the startup/shutdown prerequisite only. It does not create a GPU
launch receipt, set approval flags, or invoke the native training probe.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import time

N = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(N/'src'))
from gpu_launch_gate_r6 import collect_resources, validate_resources, file_sha
from gpu_private_ray_r6 import PrivateRayLease, TAG, owned_processes

assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
assert os.environ.get('RAY_ADDRESS') in (None, '')
assert 'ICPS_R6_GPU_APPROVED_LAUNCH' not in os.environ
import ray
assert not ray.is_initialized()
run = N/'runs'/('gpu-r6-'+secrets.token_hex(8))
run.mkdir(mode=0o700)
queue = N/'logs/gpu_private_ray_r6_live_r2'
with (queue/'run.json').open('x') as f:
    json.dump({'run':str(run),'purpose':'zero_GPU_actual_Ray_lifecycle_only'},f)

@ray.remote(num_cpus=1, num_gpus=0)
def witness():
    import os
    import ray
    context = ray.get_runtime_context()
    return dict(pid=os.getpid(), owner=os.environ.get('ICPS_R6_PROCESS_OWNER'),
                cuda_visible=os.environ.get('CUDA_VISIBLE_DEVICES'),
                namespace=context.namespace, accelerator_ids=context.get_accelerator_ids())

started = time.monotonic()
with PrivateRayLease(run) as lease:
    resources = collect_resources()
    validate_resources(resources,time.time())
    with (run/'resources_before.json').open('x') as f: json.dump(resources,f,indent=2)
    try:
        context = ray.init(address='local', namespace=run.name, _temp_dir=str(lease.temp/'ray'),
            num_cpus=1, num_gpus=0, include_dashboard=False,
            object_store_memory=128*1024**2, log_to_driver=False)
        assert ray.is_initialized()
        assert ray.cluster_resources().get('GPU',0) == 0
        task = ray.get(witness.remote(), timeout=60)
        assert task['owner'] == str(run) and task['namespace'] == run.name
        assert task['cuda_visible'] == '' and not task['accelerator_ids'].get('GPU')
        before_shutdown = owned_processes(lease.owner)
        assert task['pid'] in {x['pid'] for x in before_shutdown}
        lease.verify_owner()
        assert lease.temp.stat().st_mode & 0o777 == 0o700
        assert (lease.temp/'ray').is_dir()
        with (run/'ray_live_task.json').open('x') as f:
            json.dump(dict(task=task,owned_before_shutdown=before_shutdown,
                           resources=ray.cluster_resources()),f,indent=2)
    finally:
        ray.shutdown()  # Only the local Ray instance created by this process.
        assert not ray.is_initialized()
    # Lease exit performs an independent ownership scan and fails on leftovers.
end = json.loads((run/'ray_lifecycle_end.json').read_text())
assert not end['owned_processes_remaining'] and not end['body_failed']
assert not (run/'launch_receipt.json').exists()
assert not (run/'NEVER_SAVE_CHECKPOINT').exists()
report = dict(status='ACTUAL_PRIVATE_RAY_LIFECYCLE_PASS_ZERO_GPU',
    run_name=run.name, actual_Ray_started=True, actual_remote_task=True,
    tagged_task_owned=True, namespace_exact=True, zero_GPU_resources=True,
    Ray_shutdown_completed=True, private_parent_mode='0700', Ray_workdir='private_parent/ray',
    prior_failure='gpu_private_ray_r6_live exit1: Ray chmod of direct temp root; retained', owned_processes_remaining=[],
    wall_seconds=time.monotonic()-started, original_resource_gate_pass=True,
    source_SHA={p:file_sha(N/p) for p in ('validation/gpu_private_ray_r6_live.py',
        'ops/gpu_private_ray_r6_live.sh','src/gpu_private_ray_r6.py','src/gpu_launch_gate_r6.py')},
    GPU_started=False, model_constructed=False, optimizer_steps=0,
    production_receipt_created=False, training_admitted=False,
    limitations=['One actual CPU-only local Ray init/task/shutdown; not eight-GPU worker acceptance.',
      'Native model initialization and optimizer updates remain untested.',
      'Run/temp directories and logs retained; no global cleanup or external signals.'])
with (N/'reports/GPU_PRIVATE_RAY_R6_LIVE_R2.json').open('x') as f: json.dump(report,f,indent=2)
print(json.dumps(report))
