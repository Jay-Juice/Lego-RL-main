"""Actual cached Harbor provider/proxy integration; scripted output, no verifier."""
import asyncio
import copy
import gc
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import time
from types import SimpleNamespace
import uuid
import weakref

N = Path(__file__).resolve().parents[1]
B = N.parents[1]
F = B/'experiments/icps_v11_full97_sao_20261024_r2'
AGENT = 'docker.io/jierun/c-oh-sdk-1.33.0:v0.1'
VERIFIER = 'lego-rl/swebench-verifier-runtime:4.0.3-py311'


def preflight():
    assert shutil.disk_usage(B).free >= 200*2**30
    pins = json.loads((F/'preflight/FULL6248_PREPARED_IMAGES.json').read_text())
    directory, pin = next((Path(p), e) for p,e in sorted(pins.items()) if e['mode']=='cached_prepared')
    for file,key in [('environment/Dockerfile','Dockerfile_SHA'),('instruction.md','instruction_SHA'),('task.toml','task_config_SHA')]:
        assert hashlib.sha256((directory.parent/file).read_bytes()).hexdigest()==pin[key], key
    for tag in [pin['tag'], AGENT, VERIFIER]:
        image = json.loads(subprocess.check_output(['docker','image','inspect',tag],text=True))[0]
        if tag == pin['tag']: assert image['Id']==pin['image_id']
    # Require existing staging markers, so inherited runtime staging cannot rebuild caches.
    for tag, namespace in [(AGENT,''),(VERIFIER,'verifier_')]:
        safe = namespace+tag.replace('/','_').replace(':','_')
        assert (Path('/opt/harbor-agent-runtime-cache')/safe/'.staged_ok').is_file()
    ids = subprocess.check_output(['docker','network','ls','-q'],text=True).split()
    networks = json.loads(subprocess.check_output(['docker','network','inspect',*ids],text=True))
    pool = ipaddress.ip_network(os.environ['LEGO_EVAL_SUBNET_POOL'])
    for net in networks:
        for config in net.get('IPAM',{}).get('Config') or []:
            if config.get('Subnet') and ':' not in config['Subnet']:
                assert not pool.overlaps(ipaddress.ip_network(config['Subnet'])), 'subnet overlap'
    return directory,pin


async def main():
    from harbor.models.task.task import Task
    from harbor.models.trial.paths import TrialPaths
    from harbor_patch.environments.pooled_remote_docker import PooledRemoteDockerEnvironment
    from harbor_patch.privileged_state import registry
    from transformers import AutoTokenizer
    from verl.workers.rollout.replica import TokenOutput
    from verl_patch.agent_loop.vllm_chat_completion_proxy import _VLLMChatCompletionsProxy, _proxy_error_from_exception
    from verl_patch.agent_loop.privileged_critic_builder import interleave
    from dynamic_session_r6_r2 import R6DynamicSessionR2
    from dynamic_runtime_r6 import CACHE, CONTEXT
    import harbor_patch.environments.remote_docker as module
    assert Path(module.__file__).resolve()==N/'runtime/remote_docker.py'
    directory,pin=preflight()
    task=Task(directory.parent)
    sid='dynamic-r6-harbor-'+uuid.uuid4().hex[:12]
    paths=TrialPaths(N/'harbor_trials'/sid);paths.mkdir()
    env=PooledRemoteDockerEnvironment(environment_dir=directory,environment_name=task.name,
        session_id=sid,trial_paths=paths,task_env_config=task.config.environment,
        agent_runtime_image=AGENT,agent_runtime_mount_path='/opt/custom-agent-runtime/oh-sdk',
        agent_runtime_image_subpath='opt/custom-agent-runtime/oh-sdk',verifier_runtime_image=VERIFIER,
        verifier_runtime_mount_path='/opt/lego-verifier',verifier_runtime_image_subpath='opt/lego-verifier',
        override_cpus=2,override_memory_mb=8192)
    tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
    audit=[];latest=None;direct=None;records=[];checks=[];provider_ref=None
    class Manager:
        async def generate(self,request_id,prompt_ids,sampling_params):
            audit.append(dict(start=time.time_ns(),prompt_ids=list(prompt_ids)))
            ids=tok.encode(f'Observe workspace {len(audit)}.',add_special_tokens=False)
            return TokenOutput(token_ids=ids,log_probs=[-.125]*len(ids),stop_reason='length')
    loop=SimpleNamespace(tokenizer=tok,processor=None,server_manager=Manager(),
                         loop=asyncio.get_running_loop(),apply_chat_template_kwargs={})
    async def template(messages,tools=None,remove_system_prompt=False):
        from verl.utils.chat_template import apply_chat_template,initialize_system_prompt
        ids=apply_chat_template(tok,messages,tools=tools,tokenize=True,add_generation_prompt=True)
        return ids[len(initialize_system_prompt(tok)):] if remove_system_prompt else ids
    loop.apply_chat_template=template
    proxy=_VLLMChatCompletionsProxy(loop,'qwen3_coder',max_consecutive_no_tool=0)
    messages=[{'role':'user','content':'Observe the task workspace.'}]
    stem='pi_dynamic_probe_'+uuid.uuid4().hex[:8]
    original=f'/testbed/{stem}.py';renamed=f'/testbed/{stem}_renamed.py'
    begin=time.monotonic();cpu=time.process_time()
    async def edit(code):
        result=await env.exec(command='"${HARBOR_VERIFIER_PYTHON:-python3}" -B -c '+shlex.quote(code),timeout_sec=30)
        assert result.return_code==0,'scripted file event failed'
    async def call(label):
        nonlocal direct
        if records:messages.append({'role':'user','content':label})
        message,*_=await proxy._generate_assistant_message(sid,messages,None,{'temperature':.7,'max_tokens':16})
        messages.append(message)
        rec=copy.deepcopy(proxy._sessions[sid]['pi_call_records'][-1])
        ctx=latest[CONTEXT]
        if direct is None:direct=R6DynamicSessionR2(ctx['issue'],tok,ctx['task_uid'],sid)
        want=direct.capture(ctx['snapshot'],task_uid=ctx['task_uid'],session_id=sid,
                            logical_call_id=rec['logical_call_id'],seq=rec['state_seq'])
        assert all(rec[k]==v for k,v in want.items()),'actual provider/direct output mismatch'
        assert rec['captured_at_end_ns']<=audit[-1]['start']
        assert CONTEXT not in rec and CACHE not in rec and 'files' not in rec
        assert len(rec['pi_ids']) <= (192 if not records else 128)
        records.append(rec)
        checks.append(dict(event=label,tokens=len(rec['pi_ids']),windows=len(rec['windows']),
                           bounded_files=len(ctx['snapshot']['files']),limited=ctx['snapshot']['limited']))
        return rec
    try:
        await env.start(force_build=False)
        await env.initialize_privileged_state()
        provider=registry._providers[sid]
        provider_ref=weakref.ref(provider.__self__)
        async def observed_capture():
            nonlocal latest
            latest=await provider()
            return latest
        # Test-only observer retains the exact capture entering the actual proxy.
        registry.unregister(sid);registry.register(sid,observed_capture)
        await proxy.open_session(sid)
        await call('initial')
        assert not (await call('read-only noop'))['pi_ids']
        await edit(f'import pathlib;p=pathlib.Path({original!r});assert not p.exists();p.write_text("def pi_dynamic_probe(x):\\n    return x+1\\n")')
        added=await call('add new source file')
        assert any(w['file']==Path(original).name for w in added['windows']),'new file not selected'
        await edit(f'import pathlib;p=pathlib.Path({original!r});p.write_text("def pi_dynamic_probe(x):\\n    return x+2\\n")')
        await call('edit new source file')
        await edit(f'import pathlib;p=pathlib.Path({original!r});p.write_text("def pi_dynamic_probe(x):\\n    return x+1\\n")')
        assert (await call('rollback source'))['pi_ids']
        await edit(f'import pathlib;p=pathlib.Path({original!r});q=pathlib.Path({renamed!r});assert not q.exists();p.rename(q)')
        renamed_rec=await call('rename probe file')
        assert any(w['file']==Path(renamed).name for w in renamed_rec['windows'])
        await edit(f'import pathlib;pathlib.Path({renamed!r}).write_text("def broken(:\\n    pass\\n")')
        await call('parse failure in probe file')
        await edit(f'import pathlib;pathlib.Path({renamed!r}).unlink()')
        await call('delete only probe-created file')
        meta=await proxy.pop_session(sid)
        assert CACHE not in meta and CONTEXT not in meta
        assert task.instruction not in json.dumps(meta)
        critic,gather,mask=interleave(meta['traj_acc_ids'],meta['initial_prompt_token_len'],
                                     meta['traj_response_mask'],records,total_pi_budget=172032,tokenizer=tok)
        assert [t for t,p in zip(critic,mask) if not p]==meta['traj_acc_ids']
        assert all(critic[p+1]==meta['traj_acc_ids'][meta['initial_prompt_token_len']+i] for i,p in enumerate(gather))
        # Same scripted history with PI disabled verifies actual Harbor integration is out of band.
        os.environ['PI_ENABLE']='0';audit_on=copy.deepcopy(audit);audit.clear()
        control_sid=sid+'-control';await proxy.open_session(control_sid)
        control_messages=[{'role':'user','content':'Observe the task workspace.'}]
        for i,row in enumerate(checks):
            if i:control_messages.append({'role':'user','content':row['event']})
            message,*_=await proxy._generate_assistant_message(control_sid,control_messages,None,{'temperature':.7,'max_tokens':16})
            control_messages.append(message)
        control=await proxy.pop_session(control_sid)
        for key in ['traj_acc_ids','initial_prompt_token_len','traj_response_mask','traj_response_logprobs','traj_response_routing']:
            assert meta[key]==control[key],key
        assert [a['prompt_ids'] for a in audit_on]==[a['prompt_ids'] for a in audit]
        os.environ['PI_ENABLE']='1'
        await env.stop(delete=False)
        assert sid not in registry._providers
        del provider,observed_capture
        latest=None;gc.collect()
        assert provider_ref() is None,'provider retained after own teardown'
        try:
            await registry.capture(sid)
            raise AssertionError('closed capture accepted')
        except registry.SessionClosedError as exc:
            assert _proxy_error_from_exception(exc).status==410
        result=dict(status='passed',trial=sid,actual_Harbor=True,actual_provider=True,
                    actual_proxy=True,actual_Qwen=True,scripted_generation=True,
                    actual_Actor_rollout=False,verifier_calls=0,GPU=False,optimizer=False,
                    exact_direct_outputs=True,actor_input_and_masks_logprobs_routing_unchanged=True,
                    causal_gather=True,private_cache_removed=True,provider_weakref_released=True,
                    teardown_closed410=True,events=checks,task_SHA=hashlib.sha256(task.name.encode()).hexdigest(),
                    pinned_image_id=pin['image_id'],no_pull_or_build=True,subnet_pool=os.environ['LEGO_EVAL_SUBNET_POOL'],
                    wall_seconds=time.monotonic()-begin,CPU_seconds=time.process_time()-cpu,
                    process_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    source_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        with (N/'reports/HARBOR_DYNAMIC_R6.json').open('x') as out:json.dump(result,out,indent=2)
        print(json.dumps(result))
    finally:
        await proxy.stop()
        if getattr(env,'_explicit_network_name',None):await env.stop(delete=False)


if __name__=='__main__':asyncio.run(main())
