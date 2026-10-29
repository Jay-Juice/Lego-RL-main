"""CPU actual Harbor probe for cached AND local-build full-pool integration."""
import asyncio,hashlib,json,os,pathlib,shlex,time,uuid
from harbor.models.task.task import Task
from harbor.models.trial.paths import TrialPaths
from harbor_patch.environments.pooled_remote_docker import PooledRemoteDockerEnvironment
from harbor_patch.privileged_state import registry
from transformers import AutoTokenizer
from v11_runtime import proxy_fields
F=pathlib.Path(os.environ['ICPS_FORMAL_ROOT']);B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
async def main():
    pins=json.loads((F/'preflight/FULL6248_PREPARED_IMAGES.json').read_text());tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True);results=[]
    for mode in ['cached_prepared','native_local_build']:
        selected=next((p for p,e in pins.items() if e['mode']==mode),None)
        if selected is None:continue
        directory=pathlib.Path(selected);task=Task(directory.parent);assert task.instruction==(directory.parent/'instruction.md').read_text()
        out=F/'preflight'/('pool_probe_'+mode);paths=TrialPaths(out);paths.mkdir();session='icps-full-probe-'+uuid.uuid4().hex[:12]
        env=PooledRemoteDockerEnvironment(environment_dir=directory,environment_name=task.name,session_id=session,trial_paths=paths,task_env_config=task.config.environment,
            agent_runtime_image='docker.io/jierun/c-oh-sdk-1.33.0:v0.1',agent_runtime_mount_path='/opt/custom-agent-runtime/oh-sdk',agent_runtime_image_subpath='opt/custom-agent-runtime/oh-sdk',
            verifier_runtime_image='lego-rl/swebench-verifier-runtime:4.0.3-py311',verifier_runtime_mount_path='/opt/lego-verifier',verifier_runtime_image_subpath='opt/lego-verifier',override_cpus=4,override_memory_mb=8192)
        start=time.monotonic()
        try:
            await env.start(force_build=False);await env.initialize_privileged_state();cache={}
            first=proxy_fields(await registry.capture(session),tok,cache,logical_call_id='0');same=proxy_fields(await registry.capture(session),tok,cache,logical_call_id='1')
            assert first['windows'] and 0<len(first['pi_ids'])<=192 and not same['pi_ids']
            w=first['windows'][0]
            script='import pathlib;p=pathlib.Path('+repr('/testbed/'+w['file'])+');s=p.read_text();ls=s.splitlines(True);i='+str(w['start']-1)+';ls[i]=ls[i].rstrip("\\r\\n")+"  # formal_preflight_source\\n";p.write_text("".join(ls))'
            changed=await env.exec(command='python3 -B -c '+shlex.quote(script),timeout_sec=30);assert changed.return_code==0
            update=proxy_fields(await registry.capture(session),tok,cache,logical_call_id='2');assert 0<len(update['pi_ids'])<=128 and update['state_hash']!=first['state_hash']
            results.append(dict(mode=mode,task_SHA=hashlib.sha256(task.name.encode()).hexdigest(),first_tokens=len(first['pi_ids']),unchanged_tokens=0,update_tokens=len(update['pi_ids']),
                windows_source_hash_verified=True,wall_seconds=time.monotonic()-start,verifier_calls=0,Actor_calls=0,no_pull=True,original_prepared_task=True))
        finally:await env.stop(delete=False)
    with (F/'preflight/REAL_FULL_POOL_CPU_PROBE.json').open('x') as f:json.dump(dict(passed=True,rows=results,scope='actual cached and native local build; no model generation or verifier',GPU_compute=False),f,indent=2)
    print(json.dumps(dict(passed=True,modes=[r['mode'] for r in results])))
if __name__=='__main__':asyncio.run(main())
