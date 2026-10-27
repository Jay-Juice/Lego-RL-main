"""Freeze a strictly verified initial-only cohort from real ICPS trajectories.

No model load, task command, verifier, reward-based selection or production edit.
The canonical native proxy replay is NOT claimed identical to original sampled IDs.
"""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
                  TOKENIZERS_PARALLELISM='false', HF_HUB_OFFLINE='1', PI_ENABLE='0')
import asyncio, collections, copy, gzip, hashlib, importlib.util, json, pathlib, sys
from types import SimpleNamespace
from inventory import B, R, F, P
sys.path[:0]=[str(F/'src'),str(F/'core'),str(R/'src'),str(R/'third_party/verl'),str(R/'third_party/harbor/src')]
import torch
torch.set_num_threads(1)
from transformers import AutoTokenizer
from verl.experimental.agent_loop.agent_loop import AgentLoopBase, initialize_system_prompt
from verl_patch.agent_loop import vllm_chat_completion_proxy as proxy
from issue_program_state import build_initial_index
from window_serializer import WindowSession, digest

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(p,x):
    with pathlib.Path(p).open('x') as f: json.dump(x,f,indent=2,allow_nan=False)
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=load_module('frozen_icps_builder',F/'runtime/privileged_critic_builder.py')

def fixed_length(tokens,n,filler):
    assert n>0 and tokens and filler
    return (list(tokens)+list(filler)*((max(0,n-len(tokens))+len(filler)-1)//len(filler)))[:n]

async def main():
    os.umask(0o077)
    inventory=json.loads((P/'private_inventory.json').read_text())
    tok=AutoTokenizer.from_pretrained(str(B/'Qwen3.5-9B'),local_files_only=True)
    class Loop(AgentLoopBase):
        async def run(self,*a,**k): raise AssertionError('generation forbidden')
    loop=object.__new__(Loop);loop.tokenizer=tok;loop.processor=None;loop.loop=asyncio.get_running_loop()
    loop.apply_chat_template_kwargs={};loop.system_prompt=initialize_system_prompt(tok);loop.rollout_config=SimpleNamespace(prompt_length=98304)
    p=object.__new__(proxy._VLLMChatCompletionsProxy)
    p._processor=None;p._tokenizer=tok;p._agent_loop=loop;p._gen_prompt_len=proxy._compute_gen_prompt_len(tok,{})
    proxy._RECOMPUTE_MISMATCH_LP=False
    accepted=[];exclusions=[]
    # Frozen deterministic selection; no outcome read until all eligibility decisions.
    for row in inventory['rows']:
        if len(accepted)>=32: break
        trial=pathlib.Path(row['trial'])
        try:
            cfg=json.loads((trial/'config.json').read_text());task=pathlib.Path(cfg['task']['path'])
            if not task.is_absolute(): task=B/task
            issue=(task/'instruction.md').read_text()
            captured=json.load(gzip.open(R/'.private_icps_bug_coverage_20261023/captures'/f"{row['uid']}.json.gz",'rt'))
            assert captured['issue_SHA']==hashlib.sha256(issue.encode()).hexdigest(), 'instruction identity'
            snapshot=captured['snapshot'];audit=json.loads((trial/'pi_calls.json').read_text())
            task_uid=digest(['icps_task',task.name]);session=audit['session_id']
            idx=build_initial_index(snapshot,issue,task_uid=task_uid,session_id=session)
            candidates=[{k:v for k,v in e.items() if k in {'file','qualified','entity_id','kind','start_line','end_line','syntax','selection','tier','retrieval_score'}} for e in idx['focus']]
            w=WindowSession(candidates,issue,tok,task_uid,session)
            result=w.capture(snapshot,task_uid=task_uid,session_id=session,logical_call_id='initial',seq=0)
            first=audit['records'][0]
            assert result['state_hash']==first['state_hash'], 'complete candidate state hash'
            assert len(result['pi_ids'])==first['tokens'], 'initial PI token count'
            for key in ['unknown']:
                assert result[key]==first[key], key
            keys=['file','qualified','start','end','source_hash','file_sha','partial','syntax']
            assert [{k:v.get(k) for k in keys} for v in result['windows']]==first['windows'], 'all window metadata'
            assert all(r['state_hash']==first['state_hash'] for r in audit['records']), 'state changed'
            assert all(r['tokens']==0 for r in audit['records'][1:]), 'additional PI'
            trajectory=json.loads((trial/'proxy_trajectory.json').read_text())
            # Force the unchanged, native rebuild branch in this isolated CPU process.
            sess={'messages_snapshot':[{'role':'system','content':'diagnostic sentinel'}], 'last_tools':None}
            actor=await p._compute_prompt_ids(sess,trajectory['messages_snapshot'],trajectory['tools'],'frozen-diagnostic')
            plen=sess['initial_prompt_token_len'];mask=sess['traj_response_mask']
            assert len(actor)==plen+len(mask) and sum(mask)>0
            assert len(actor)<=73728, 'native actor reserve 73728; no truncation'
            assert len(mask)<=65536, 'baseline response cap; no truncation'
            assert mask[0]==1 and len(result['pi_ids'])>0
            spans=[];start=None
            for i,m in enumerate(mask+[0]):
                if m and start is None:start=plen+i
                if not m and start is not None:spans.append((start,plen+i));start=None
            records=[dict(state_hash=first['state_hash'],pi_format='icps_window_v11',pi_ids=result['pi_ids'] if j==0 else [],pi_text=result['pi_text'] if j==0 else '',actor_response_start_abs=a,actor_response_end_abs=b,valid=True) for j,(a,b) in enumerate(spans)]
            ids,gather,pi_mask=builder.interleave(actor,plen,mask,records)
            assert [x for x,m in zip(ids,pi_mask) if not m]==actor
            assert [ids[g+1] for g in gather]==actor[plen:]
            accepted.append(dict(**row, family=row['task_id'].split('.')[0],actor_ids=actor,prompt_len=plen,response_mask=mask,
                                 true_pi_ids=result['pi_ids'],records=records,pi_text=result['pi_text'],spans=spans,
                                 provenance={n:sha(trial/n) for n in ['pi_calls.json','proxy_trajectory.json','config.json']},
                                 W0_capture_SHA=sha(R/'.private_icps_bug_coverage_20261023/captures'/f"{row['uid']}.json.gz")))
        except (AssertionError,ValueError,KeyError,FileNotFoundError) as e:
            exclusions.append(dict(selection_key=row['selection_key'],reason=str(e)[:180]))
    assert len(accepted)>=8 and len({r['family'] for r in accepted})>=4, 'insufficient pilot coverage'
    filler=tok.encode(' unspecified',add_special_tokens=False)
    special=set(tok.all_special_ids)
    for i,row in enumerate(accepted):
        n=len(row['true_pi_ids'])
        donor=next(r for r in accepted[i+1:]+accepted[:i] if r['family']!=row['family'])
        controls={'true':row['true_pi_ids'], 'neutral':fixed_length(filler,n,filler),
                  'wrong':fixed_length(donor['true_pi_ids'],n,filler)}
        assert all(len(v)==n and not special.intersection(v) for v in controls.values())
        assert controls['true']!=controls['neutral'] and controls['true']!=controls['wrong']
        row['wrong_donor']=donor['selection_key'];row['views']={}
        for condition,pi_ids in [*controls.items(),('history',[])]:
            records=copy.deepcopy(row['records']);records[0]['pi_ids']=pi_ids
            ids,gather,pi_mask=builder.interleave(row['actor_ids'],row['prompt_len'],row['response_mask'],records)
            assert [x for x,m in zip(ids,pi_mask) if not m]==row['actor_ids']
            row['views'][condition]=dict(input_ids=ids,gather=gather,pi_mask=pi_mask)
        for c in ['neutral','wrong']:
            assert row['views'][c]['gather']==row['views']['true']['gather']
            assert row['views'][c]['pi_mask']==row['views']['true']['pi_mask']
        reward_path=pathlib.Path(row['trial'])/'verifier/reward.txt'
        try:
            reward=float(reward_path.read_text().strip());assert reward in (0,1)
        except (ValueError,FileNotFoundError,AssertionError):reward=None
        row['reward']=reward;row['reward_SHA']=sha(reward_path) if reward_path.is_file() else None
    cache=dict(rows=accepted, config=json.loads((F/'runs/full_20261023T180705Z_3600076/resolved_actual.json').read_text()),
               scope='Native canonical proxy replay on actual ICPS trajectories with hash-proven constant initial PI. Not original sampled-token archive; initial-only and <=73728 cohort. No claim about dynamic-update trajectories.')
    target=P/'private_cache_full.pt'
    with target.open('xb') as f:torch.save(cache,f)
    receipt=dict(passed=True,cache_SHA=sha(target),cache_bytes=target.stat().st_size,selected=len(accepted),families=len({r['family'] for r in accepted}),
                 selected_before_outcomes=True,positive=sum(r['reward']==1 for r in accepted),negative=sum(r['reward']==0 for r in accepted),unscored=sum(r['reward'] is None for r in accepted),
                 initial_state_and_window_metadata_verified=True,identical_Actor_and_action_mask_across_conditions=True,equal_length_true_neutral_wrong=True,
                 model_loads=0,GPU_runs=0,optimizer_steps=0,scope=cache['scope'],exclusions=exclusions,
                 source_SHA={str(q.relative_to(F)):sha(q) for q in [F/'src/window_serializer.py',F/'core/issue_program_state.py',F/'runtime/privileged_critic_builder.py']},
                 samples=[dict(selection_key=r['selection_key'],source_step=r['source_step'],family=r['family'],actor_tokens=len(r['actor_ids']),pi_tokens=len(r['true_pi_ids']),actions=sum(r['response_mask']),reward=r['reward']) for r in accepted])
    save(P/'CACHE_FULL_RECEIPT.json',receipt)
    assert not torch.cuda.is_initialized()
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['exclusions','samples','source_SHA']},ensure_ascii=True))

if __name__=='__main__': asyncio.run(main())
