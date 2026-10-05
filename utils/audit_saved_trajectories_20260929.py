"""CPU-only retrospective message reconstruction, NOT raw rollout-token proof."""
import ast
import collections
import hashlib
import json
import pathlib
import random
from typing import Any
from transformers import AutoTokenizer
from verl.utils.chat_template import initialize_system_prompt, apply_chat_template
from verl.utils.tokenizer import normalize_token_ids

ROOT = pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
OUT = ROOT/'logs/swesmith_trajectory_audit_20260929.json'
BASE = ROOT/'harbor_trials/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1'

def main():
    assert not OUT.exists()
    candidates = []
    for step in range(1,131):
        parent = BASE if step <= 70 else BASE/'resume70_metadatafix_20260928'
        for p in sorted((parent/f'step_{step:04d}').glob('*/proxy_trajectory.json')):
            rewardfile = p.parent/'verifier/reward.txt'
            if not rewardfile.exists():
                continue
            reward = float(rewardfile.read_text().strip())
            candidates.append(dict(path=str(p),step=step,reward=reward,size=p.stat().st_size))
    rng = random.Random(20260929)
    selected = {}
    for lo,hi in [(1,19),(20,39),(40,70),(71,100),(101,130)]:
        for reward in [0.,1.]:
            group = [x for x in candidates if lo <= x['step'] <= hi and x['reward']==reward]
            longest = sorted(group,key=lambda x:x['size'],reverse=True)[:3]
            for x in longest:
                selected[x['path']] = dict(**x,stratum='longest_by_phase_reward')
            rest = [x for x in group if x['path'] not in selected]
            for x in rng.sample(rest,min(7,len(rest))):
                selected[x['path']] = dict(**x,stratum='random_by_phase_reward')
    tok = AutoTokenizer.from_pretrained(str(ROOT/'Qwen3.5-9B'),local_files_only=True)
    system = initialize_system_prompt(tok)
    src = (ROOT/'src/verl_patch/agent_loop/vllm_chat_completion_proxy.py').read_text()
    names = {'_normalize_openai_messages_for_template','_compute_gen_prompt_len'}
    nodes = [n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in names]
    import logging
    ns = dict(Any=Any,json=json,normalize_token_ids=normalize_token_ids,logger=logging.getLogger('audit'))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<proxy_helpers>','exec'),ns)
    gp = ns['_compute_gen_prompt_len'](tok,{})
    def encode(messages,tools=None,remove=False):
        ids = normalize_token_ids(apply_chat_template(tok,messages,tools=tools,add_generation_prompt=True,tokenize=True))
        return ids[len(system):] if remove else ids
    results = []
    for item in selected.values():
        p = pathlib.Path(item['path']); raw=p.read_bytes(); x=json.loads(raw)
        messages=ns['_normalize_openai_messages_for_template'](x['messages_snapshot'])
        first=next((i for i,m in enumerate(messages) if m['role']=='assistant'),len(messages))
        prefix=encode(messages[:first],x.get('tools'))
        segments=[];pos=0;clipped_pos=0;edits=[];i=first
        while i<len(messages):
            assistant=messages[i]['role']=='assistant'; j=i+1
            if not assistant:
                while j<len(messages) and messages[j]['role']!='assistant': j+=1
            ids=encode(messages[i:j],remove=True)
            clipped=ids[-8192:]
            if assistant and gp:
                ids=ids[gp:-gp];clipped=clipped[gp:-gp]
            segments.append(dict(message=i,role='assistant' if assistant else 'observation',
                                 start=pos,length=len(ids),capped_start=clipped_pos,capped_length=len(clipped)))
            if assistant:
                for call in messages[i].get('tool_calls',[]):
                    fn=call['function'];args=fn.get('arguments',{})
                    if fn['name']=='file_editor' and args.get('command') in ['str_replace','create','insert','undo_edit']:
                        edits.append(dict(message=i,command=args['command'],path=args.get('path'),
                                          start=pos,capped_start=clipped_pos))
            pos+=len(ids);clipped_pos+=len(clipped);i=j
        model=sum(s['length'] for s in segments if s['role']=='assistant')
        retained_model=sum(max(0,min(s['length'],65536-s['start'])) for s in segments if s['role']=='assistant')
        patch=p.parent/'artifacts/predict_patch.diff'
        results.append(dict(**item,sha256=hashlib.sha256(raw).hexdigest(),initial_prompt_tokens=len(prefix),
            reconstructed_response_tokens=pos,rebuild_capped_response_tokens=clipped_pos,
            reconstructed_assistant_tokens=model,reconstructed_observation_tokens=pos-model,
            reconstructed_retained_assistant_tokens=retained_model,
            over_window=pos>65536,over_window_even_with_segment_cap=clipped_pos>65536,
            edits_after_window=[e for e in edits if e['start']>=65536],
            edits_after_window_with_segment_cap=[e for e in edits if e['capped_start']>=65536],
            debug_sources=sorted({z['source'] for z in x.get('message_snap_debug',[])}),
            patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest() if patch.exists() else None,
            segments=segments))
        print('trajectory',len(results),item['step'],item['reward'],pos,clipped_pos,flush=True)
    summary=dict(candidate_count=len(candidates),sample_count=len(results),
        estimated_over_window=sum(x['over_window'] for x in results),
        over_window_even_with_segment_cap=sum(x['over_window_even_with_segment_cap'] for x in results),
        successful_with_late_edits=sum(x['reward']==1 and bool(x['edits_after_window_with_segment_cap']) for x in results),
        note='Saved messages retokenized using frozen tokenizer/template; original token arrays and masks not persisted. Two reconstructions are sensitivity checks, not exact original offsets. Length-enriched stratified sample; not population rate.',
        results=results)
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=False))

if __name__=='__main__': main()
