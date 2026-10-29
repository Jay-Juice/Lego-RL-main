"""Adaptive development follow-up: preserve joint seeds, refill original context.

No new retrieval or relevance model. Restore contiguous growth after the joint
stage; a prior selected source line can never be dropped. Not independent proof.
"""
from joint_context_r7 import joint, payload, MeteredCache
from fast_allocation_r7 import serialize as reference
from window_serializer import resolve, query, terms, sha
from dense_state import render, overlap

ARMS={m:(1024,8,True) for m in ('control1024_8','joint_refill1024_8','joint_centered_refill1024_8')}


def refill(z,candidates,snapshot,issue,tokenizer):
    chosen=[dict(w) for w in z['windows']]
    current={e['entity_id']:e for e in resolve(candidates,snapshot['files']) if e['available']}
    lines={e['file']:snapshot['files'][e['file']].splitlines(True) for e in current.values()}
    q,_=query(issue);cache={};steps=0
    def feature(line):
        if line not in cache:cache[line]=len(terms(line)&q)
        return cache[line]
    def cost(ws):return len(tokenizer.encode(render(ws,snapshot.get('limited',False)),add_special_tokens=False))
    while chosen:
        prior=cost(chosen);options=[]
        for i,w in enumerate(chosen):
            e=current[w['entity_id']]
            for a,b in ((w['start']-1,w['end']),(w['start'],w['end']+1)):
                if a<e['start_line'] or b>e['end_line']:continue
                if any(j!=i and x['file']==w['file'] and overlap((a,b),(x['start'],x['end'])) for j,x in enumerate(chosen)):continue
                code=''.join(lines[w['file']][a-1:b])
                nw=dict(w,start=a,end=b,code=code,source_hash=sha(code),partial=a!=e['start_line'] or b!=e['end_line'],unit='expanded_context')
                trial=chosen[:i]+[nw]+chosen[i+1:];tokens=cost(trial)
                if tokens>1024:continue
                added=lines[w['file']][a-1] if a<w['start'] else lines[w['file']][b-1]
                options.append((-feature(added),tokens-prior,w['rank'],a,i,nw))
        if not options:break
        *_,i,nw=min(options,key=lambda x:x[:-1]);chosen[i]=nw;steps+=1
    for before in z['windows']:
        assert any(w['entity_id']==before['entity_id'] and w['start']<=before['start']<=before['end']<=w['end'] for w in chosen)
    result=payload(chosen,snapshot,tokenizer)
    result['allocation_actions']=dict(z.get('allocation_actions',{}),refill_steps=steps)
    return result


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ARMS:raise ValueError('predeclared refill arm')
    if arm=='control1024_8':return reference(candidates,snapshot,issue,tokenizer,arm='fast1024_8')
    z=joint(candidates,snapshot,issue,tokenizer,centered=arm=='joint_centered_refill1024_8')
    return refill(z,candidates,snapshot,issue,tokenizer)
