"""Fixed1024 development study: local windows compete with context, no retrieval.

Only current cached source/issue are inputs. No labels or model calls. Exact
full-payload tokenization admits every action. Whole lines, not semantic closure,
are guaranteed; all windows remain explicitly partial.
"""
import ast
import copy
import functools
import inspect
import math
import textwrap
from fast_allocation_r7 import serialize as control, compiled as fast_compiled
from fast_allocation_r7 import candidate_order, MeteredCache
from window_research_r7 import marginal_score
from window_serializer import resolve, query, terms, sha, digest
from dense_state import validate, proposals, render, overlap
from executable_windows import line_signals

ARMS = {name:(1024,8,True) for name in
        ('control1024_8','centered1024_8','joint1024_8','joint_centered1024_8')}
MAX_ACTIONS=64


def centered_proposals(candidates,snapshot,issue,variant='flow_expand'):
    """Add centered3-line seeds at the SAME existing top12 executable anchors."""
    out=proposals(candidates,snapshot,issue,variant=variant)
    known={(w['entity_id'],w['start'],w['end']) for w in out}
    for rank,e in enumerate(resolve(candidates,snapshot['files'])):
        if not e['available']:continue
        lines=snapshot['files'][e['file']].splitlines(True)
        scores,_,_=line_signals(e,lines,issue,flow=True)
        anchors=sorted((i for i in scores if scores[i]>0),key=lambda i:(-scores[i],i))[:12]
        for anchor in anchors:
            a=max(e['start_line'],anchor-1);b=min(e['end_line'],anchor+1)
            key=(e['entity_id'],a,b)
            if key in known:continue
            known.add(key);code=''.join(lines[a-1:b])
            out.append(dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],rank=rank,
                start=a,end=b,code=code,source_hash=sha(code),syntax=e.get('syntax','valid'),
                partial=a!=e['start_line'] or b!=e['end_line'],low_confidence=False,
                score=scores[anchor]+sum(scores.get(i,0) for i in range(a,b+1))/(b-a+1),
                unit='context',changed_lines=0))
    return sorted(out,key=lambda w:(-w['score'],w['rank'],w['file'],w['start'],-(w['end']-w['start'])))


@functools.lru_cache(maxsize=1)
def centered_compiled():
    # Scoped function globals; original allocator/runtime are never mutated.
    import types
    f=fast_compiled(1024,8)
    return types.FunctionType(f.__code__,dict(f.__globals__,proposals=centered_proposals),
                              argdefs=f.__defaults__,closure=f.__closure__)


def payload(chosen,snapshot,tokenizer):
    text=render(chosen,snapshot.get('limited',False)) if chosen else '[PI D1 unknown no_window_fits]\n'
    ids=tokenizer.encode(text,add_special_tokens=False)
    if len(ids)>1024:raise ValueError('exact payload budget')
    maps=[]
    for w in chosen:
        lines=snapshot['files'][w['file']].splitlines(True)
        assert w['code']==''.join(lines[w['start']-1:w['end']])
        maps.append(dict(entity_id=w['entity_id'],file=w['file'],qualified=w['qualified'],path_only_visible=False,
            source_hash=sha(w['code']),file_sha=sha(snapshot['files'][w['file']]),
            pi_emitted_source_spans_W0=[dict(line=n,start_column=0,end_column=len(lines[n-1].rstrip('\r\n').encode()),line_complete=True)
                                       for n in range(w['start'],w['end']+1)]))
    return dict(pi_text=text,pi_ids=ids,pi_raw_tokens=len(ids),token_cap=1024,pi_truncated=True,
        source_map=maps,windows=chosen,unknown=not chosen,omitted=not chosen,
        semantic_hash=digest([(w['file'],w['code']) for w in chosen]),source_lines=sum(w['end']-w['start']+1 for w in chosen),
        metadata_tokens_standalone=len(tokenizer.encode(render([dict(w,code='') for w in chosen],snapshot.get('limited',False)),add_special_tokens=False)),
        source_tokens_standalone=len(tokenizer.encode(''.join(w['code'] for w in chosen),add_special_tokens=False)))


def joint(candidates,snapshot,issue,tokenizer,centered=False):
    validate(snapshot)
    props=(centered_proposals if centered else proposals)(candidates,snapshot,issue,variant='flow_expand')
    current={e['entity_id']:e for e in resolve(candidates,snapshot['files']) if e['available']}
    lines={p:s.splitlines(True) for p,s in snapshot['files'].items() if any(e['file']==p for e in current.values())}
    scores={k:line_signals(e,lines[e['file']],issue,flow=True)[0] for k,e in current.items()}
    boundaries={}
    for k,e in current.items():
        # Whole bounded statements may extend a growth chunk; never add remote code.
        boundaries[k]=[(n.lineno,n.end_lineno) for n in ast.walk(e['node'])
                       if isinstance(n,ast.stmt) and not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))
                       and n.end_lineno-n.lineno<8] if e.get('node') else []
    text=lambda ws:render(ws,snapshot.get('limited',False))
    cost=lambda ws:len(tokenizer.encode(text(ws),add_special_tokens=False))
    q,_=query(issue);tc={}
    def features(code):
        if code not in tc:tc[code]=terms(code)&q
        return tc[code]
    chosen=[];seen=set()
    # Protect four relevance-selected seeds, using the same original utility.
    for _ in range(4):
        prior=cost(chosen);options=[]
        for order,w in candidate_order(props,chosen,seen,q,text,cost,tokenizer,1024,'diverse6'):
            f=features(w['code']);u=marginal_score(w['score'],f,seen,cost(chosen+[w])-prior,'diverse6')
            u/=math.sqrt(1+w['rank'])*(1+sum(x['entity_id']==w['entity_id'] for x in chosen))
            options.append((-u,order,w))
        if not options:break
        w=copy.deepcopy(min(options,key=lambda x:x[:2])[2]);chosen.append(w);seen|=features(w['code'])
    # Standalone addition costs/features are cached once; no repeated full-bank tokenization.
    seed_data=[];header=text([])
    for order,w in enumerate(props):
        body=text([w])[len(header):]
        seed_data.append((order,w,max(1,len(tokenizer.encode(body,add_special_tokens=False))),features(w['code'])))
    counts={'add':0,'grow':0,'actions':0}
    for _ in range(MAX_ACTIONS):
        prior=cost(chosen);seen=set().union(*(features(w['code']) for w in chosen)) if chosen else set()
        options=[]
        def offer(w,idx,score,f,estimate,order):
            if score<=0:return
            repeated=1+sum(x['entity_id']==w['entity_id'] for j,x in enumerate(chosen) if j!=idx)
            numer=score/(1+len(f&seen)/max(1,len(f)))/math.sqrt(1+w['rank'])/repeated
            options.append((-numer/math.sqrt(max(1,estimate)),order,idx,w,numer))
        if len(chosen)<8:
            for order,w,estimate,f in seed_data:
                if any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in chosen):continue
                offer(w,None,w['score'],f,estimate,order)
        for i,w in enumerate(chosen):
            e=current[w['entity_id']];lo,hi=e['start_line'],e['end_line'];ss=scores[w['entity_id']]
            for side in (0,1):
                a=max(lo,w['start']-3) if side==0 else w['start']
                b=w['end'] if side==0 else min(hi,w['end']+3)
                # Complete a small boundary statement if it fits within8 new lines.
                for x,y in boundaries[w['entity_id']]:
                    if side==0 and x<a<=y<w['start'] and w['start']-x<=8:a=max(lo,x)
                    if side==1 and w['end']<x<=b<y and y-w['end']<=8:b=min(hi,y)
                if (a,b)==(w['start'],w['end']):continue
                if any(j!=i and x['file']==w['file'] and overlap((a,b),(x['start'],x['end'])) for j,x in enumerate(chosen)):continue
                new_lines=list(range(a,w['start']))+list(range(w['end']+1,b+1))
                values=[ss.get(n,0) for n in new_lines]
                score=max(values,default=0)+sum(values)/max(1,len(values))
                code=''.join(lines[w['file']][a-1:b]);added=''.join(lines[w['file']][n-1] for n in new_lines)
                nw=dict(w,start=a,end=b,code=code,source_hash=sha(code),partial=a!=lo or b!=hi,unit='expanded_context')
                offer(nw,i,score,features(added),len(tokenizer.encode(added,add_special_tokens=False)),len(props)+2*i+side)
        if not options:break
        options.sort(key=lambda x:x[:2]);selected=None
        for start in range(0,len(options),8):
            feasible=[]
            for _,order,idx,w,numer in options[start:start+8]:
                trial=chosen+[w] if idx is None else chosen[:idx]+[w]+chosen[idx+1:]
                actual=cost(trial)
                if actual<=1024:feasible.append((-numer/math.sqrt(max(1,actual-prior)),order,idx,w))
            if feasible:selected=min(feasible,key=lambda x:x[:2]);break
        if selected is None:break
        _,_,idx,w=selected
        if idx is None:chosen.append(copy.deepcopy(w));counts['add']+=1
        else:chosen[idx]=w;counts['grow']+=1
        counts['actions']+=1
    z=payload(chosen,snapshot,tokenizer);z['allocation_actions']=counts
    return z


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ARMS:raise ValueError('predeclared joint-context arm')
    if arm=='control1024_8':return control(candidates,snapshot,issue,tokenizer,arm='fast1024_8')
    if arm=='centered1024_8':return centered_compiled()(candidates,snapshot,issue,tokenizer,budget=1024,variant='diverse6')
    return joint(candidates,snapshot,issue,tokenizer,centered=arm=='joint_centered1024_8')
