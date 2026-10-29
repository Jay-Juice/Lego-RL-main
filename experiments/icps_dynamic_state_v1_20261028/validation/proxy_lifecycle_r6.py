"""Actual proxy boundaries: retries, concurrency, identity, natural exhaustion.

Uses actual Qwen tokenization and scripted generation; no Docker or GPU.
"""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

N=Path(__file__).resolve().parents[1]


async def main():
    from transformers import AutoTokenizer
    from harbor_patch.privileged_state import registry
    from verl.workers.rollout.replica import TokenOutput
    from verl_patch.agent_loop.vllm_chat_completion_proxy import _VLLMChatCompletionsProxy
    from dynamic_runtime_r6 import Capture,CACHE,CONTEXT
    from dynamic_session_r6_r2 import R6DynamicSessionR2
    tok=AutoTokenizer.from_pretrained(N.parents[1]/'Qwen3.5-9B',local_files_only=True)
    sources={};captures={};fail_sid=None;generate_calls={};poison={};overlap={'active':0,'max':0}
    def source(v):return dict(files={'a.py':f'def f(x):\n    return x+{v}\n'},stable=True,limited=False)
    class Manager:
        async def generate(self,request_id,prompt_ids,sampling_params):
            nonlocal fail_sid
            # The wrapper only provides deterministic failure/latency; real proxy owns retry identity.
            sid=current_sid.get()
            generate_calls[sid]=generate_calls.get(sid,0)+1
            if fail_sid==sid:
                fail_sid=None
                raise RuntimeError('SCRIPTED_TRANSIENT_GENERATION_FAILURE')
            overlap['active']+=1;overlap['max']=max(overlap['max'],overlap['active'])
            try:await asyncio.sleep(.01)
            finally:overlap['active']-=1
            ids=tok.encode('Observed.',add_special_tokens=False)
            return TokenOutput(token_ids=ids,log_probs=[-.1]*len(ids),stop_reason='length')
    import contextvars
    current_sid=contextvars.ContextVar('probe_session')
    loop=SimpleNamespace(tokenizer=tok,processor=None,server_manager=Manager(),
                         loop=asyncio.get_running_loop(),apply_chat_template_kwargs={})
    async def template(messages,tools=None,remove_system_prompt=False):
        from verl.utils.chat_template import apply_chat_template,initialize_system_prompt
        ids=apply_chat_template(tok,messages,tools=tools,tokenize=True,add_generation_prompt=True)
        return ids[len(initialize_system_prompt(tok)):] if remove_system_prompt else ids
    loop.apply_chat_template=template
    proxy=_VLLMChatCompletionsProxy(loop,'qwen3_coder',max_consecutive_no_tool=0)
    histories={}
    async def new(sid):
        sources[sid]=source(1)
        async def scanner():return sources[sid]
        capture=Capture('function f returns an integer','task-'+sid,sid,scanner)
        async def provider():
            result=await capture.capture();captures[sid]=copy.deepcopy(result)
            if poison.get(sid)=='identity':result['session_id']='wrong-session'
            elif poison.get(sid)=='late':result['state_seq']=0
            return result
        registry.register(sid,provider)
        histories[sid]=[{'role':'user','content':'Inspect f.'}]
        await proxy.open_session(sid)
    async def call(sid,append=True):
        token=current_sid.set(sid)
        try:
            message,*_=await proxy._generate_assistant_message(sid,histories[sid],None,{'max_tokens':8})
            if append:histories[sid].extend([message,{'role':'user','content':'Inspect again.'}])
            return proxy._sessions[sid]['pi_call_records'][-1]
        finally:current_sid.reset(token)
    async def expected_error(sid,text):
        try:await call(sid)
        except (RuntimeError,ValueError) as exc:assert text in str(exc),(text,str(exc))
        else:raise AssertionError('negative was accepted: '+text)
    results={};start=time.monotonic()
    try:
        sid='lifecycle-same-retry';await new(sid);fail_sid=sid
        await expected_error(sid,'SCRIPTED_TRANSIENT_GENERATION_FAILURE')
        cache=copy.deepcopy(proxy._sessions[sid][CACHE]);pending=copy.deepcopy(proxy._sessions[sid]['pi_pending_record'])
        rec=await call(sid)
        assert cache==proxy._sessions[sid][CACHE]
        for key in ['pi_ids','pi_text','logical_call_id','state_hash','captured_at_start_ns','captured_at_end_ns']:
            assert rec[key]==pending[key],key
        assert len(proxy._sessions[sid]['pi_call_records'])==1
        results['same_logical_retry_exact_once']=True

        sid='lifecycle-changed-retry';await new(sid);fail_sid=sid
        await expected_error(sid,'SCRIPTED_TRANSIENT_GENERATION_FAILURE')
        cache=copy.deepcopy(proxy._sessions[sid][CACHE]);sources[sid]=source(2)
        await expected_error(sid,'retry state changed')
        assert cache==proxy._sessions[sid][CACHE] and generate_calls[sid]==1
        results['changed_retry_transactional_rejection']=True

        for bad,error in [('identity','cross-task'),('late','nonmonotonic')]:
            sid='lifecycle-'+bad;await new(sid);await call(sid)
            cache=copy.deepcopy(proxy._sessions[sid][CACHE]);poison[sid]=bad
            await expected_error(sid,error)
            assert cache==proxy._sessions[sid][CACHE] and generate_calls[sid]==1
        results['wrong_identity_and_late_before_generation']=True

        await new('concurrent-a');await new('concurrent-b');sources['concurrent-b']=source(99)
        a,b=await asyncio.gather(call('concurrent-a'),call('concurrent-b'))
        assert overlap['max']>=2 and a['pi_ids']!=b['pi_ids']
        assert proxy._sessions['concurrent-a'][CACHE]['identity']!=proxy._sessions['concurrent-b'][CACHE]['identity']
        results['concurrent_sessions_isolated']=True

        sid='lifecycle-exhaustion';await new(sid)
        direct=R6DynamicSessionR2('function f returns an integer',tok,'task-'+sid,sid)
        spent=0;emitted=[]
        for i in range(256):
            sources[sid]=source(i)
            rec=await call(sid)
            want=direct.capture(sources[sid],task_uid='task-'+sid,session_id=sid,
                                logical_call_id=rec['logical_call_id'],seq=rec['state_seq'])
            assert all(rec[k]==v for k,v in want.items())
            spent+=len(rec['pi_ids']);emitted.append(len(rec['pi_ids']))
            assert spent<=4096 and len(rec['pi_ids'])<=(192 if i==0 else 128)
            if direct.exhausted:break
        assert direct.exhausted and 'exhausted' in rec['pi_text']
        sources[sid]=source(9999);empty=await call(sid)
        assert not empty['pi_ids'] and empty['unknown'] and empty['omitted']
        assert proxy._sessions[sid][CACHE]['state']['remaining']==4096-spent
        results['natural_exhaustion']=dict(calls_before_empty=i+1,spent=spent,remaining=4096-spent,
                                            max_update=max(emitted[1:]),subsequent_empty_unknown=True)
        for sid in histories:
            meta=await proxy.pop_session(sid)
            assert CACHE not in meta and CONTEXT not in meta
        results.update(status='passed',actual_proxy=True,actual_Qwen=True,scripted_generation=True,
                       synthetic_workspace=True,actual_Actor_rollout=False,GPU=False,optimizer=False,
                       wall_seconds=time.monotonic()-start,expected_errors=5,
                       source_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        with (N/'reports/PROXY_LIFECYCLE_R6.json').open('x') as out:json.dump(results,out,indent=2)
        print(json.dumps(results))
    finally:
        for sid in histories:registry.unregister(sid)
        await proxy.stop()


if __name__=='__main__':asyncio.run(main())
