"""Separate R7 development-only window hypotheses; no IO, labels or runtime patch."""
import copy
import ast
import math
from window_serializer import resolve, query, terms, sha, digest
from dense_state import validate, proposals, render, overlap, serialize as frozen_serialize

VARIANTS = ('rank6','diverse6','atomic3','atomic_rank6','compact3')
from executable_windows import line_signals
from budget_ablation_r7 import experimental_serializer

def marginal_score(score, features, seen, marginal_cost, variant):
    repeated=len(features & seen)/max(1,len(features))
    utility=score/(1+repeated)
    utility/=max(1,marginal_cost)**.5
    return utility

def with_statements(props, candidates, snapshot, issue):
    """Add bounded complete source statements; no target-coordinate knowledge."""
    out=list(props); existing={(w['entity_id'],w['start'],w['end']) for w in props}
    for rank,e in enumerate(resolve(candidates,snapshot['files'])):
        if not e['available'] or e.get('node') is None: continue
        lines=snapshot['files'][e['file']].splitlines(True)
        scores,_,_=line_signals(e,lines,issue,flow=True)
        extra=[]; seen=set()
        for node in ast.walk(e['node']):
            if not isinstance(node,ast.stmt) or isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): continue
            if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str): continue
            a,b=node.lineno,node.end_lineno; key=(e['entity_id'],a,b)
            if not e['start_line']<=a<=b<=e['end_line'] or b-a+1>8 or key in existing or key in seen: continue
            seen.add(key); strength=max((scores.get(i,0) for i in range(a,b+1)),default=0)
            score=strength+sum(scores.get(i,0) for i in range(a,b+1))/(b-a+1)
            code=''.join(lines[a-1:b])
            extra.append(dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],rank=rank,
                              start=a,end=b,code=code,source_hash=sha(code),syntax=e.get('syntax','valid'),
                              unit='complete_statement',score=score,changed_lines=0,
                              partial=a!=e['start_line'] or b!=e['end_line'],low_confidence=strength==0))
        extra.sort(key=lambda w:(-w['score'],w['end']-w['start'],w['start']))
        out.extend(extra[:24])
    return sorted(out,key=lambda w:(-w['score'],w['rank'],w['file'],w['start'],-(w['end']-w['start'])))


def serialize(candidates, snapshot, issue, tokenizer, *, budget=192, variant='rank6'):
    if variant not in VARIANTS or not budget == 256:
        raise ValueError('prototype variant/budget')
    validate(snapshot)
    chosen = []
    def text(ws): return render(ws, snapshot.get('limited', False))
    def cost(ws): return len(tokenizer.encode(text(ws), add_special_tokens=False))
    props = proposals(candidates, snapshot, issue, variant='flow_expand')
    if variant in {'atomic3','atomic_rank6','compact3'}:
        props = with_statements(props, candidates, snapshot, issue)
    q, _ = query(issue); seen = set()
    while len(chosen) < 3:
        opts=[]; prior_cost=cost(chosen)
        for order,w in enumerate(props):
            if any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in chosen):continue
            trial_cost=cost(chosen+[w])
            if trial_cost>budget:continue
            features=terms(w['code'])&q
            utility=marginal_score(w['score'],features,seen,trial_cost-prior_cost,variant)
            if variant in {'rank6','diverse6','atomic_rank6'}:
                utility /= math.sqrt(1+w['rank'])
            if variant == 'diverse6':
                utility /= 1+sum(x['entity_id']==w['entity_id'] for x in chosen)
            opts.append((-utility,order,w,features))
        if not opts:break
        _,_,w,features=min(opts,key=lambda x:x[:2]);chosen.append(copy.deepcopy(w));seen|=features
    if not chosen:
        return experimental_serializer()(candidates,snapshot,issue,tokenizer,budget=budget,variant='novelty_cost_expand')
    current = {e['entity_id']: e for e in resolve(candidates, snapshot['files'])}
    q, _ = query(issue)
    while chosen and variant != 'compact3':
        options = []
        for i, w in enumerate(chosen):
            e = current[w['entity_id']]; lines = snapshot['files'][w['file']].splitlines(True)
            for a, b in [(w['start']-1, w['end']), (w['start'], w['end']+1)]:
                if a < e['start_line'] or b > e['end_line']: continue
                if any(j != i and x['file'] == w['file'] and overlap((a,b),(x['start'],x['end'])) for j,x in enumerate(chosen)): continue
                code = ''.join(lines[a-1:b])
                nw = dict(w,start=a,end=b,code=code,source_hash=sha(code),unit='expanded_context' if w.get('unit') in {'complete_statement','expanded_context'} else w.get('unit','context'),partial=a!=e['start_line'] or b!=e['end_line'])
                trial = chosen[:i]+[nw]+chosen[i+1:]
                if cost(trial) > budget: continue
                line = lines[a-1] if a < w['start'] else lines[b-1]
                options.append((-len(terms(line)&q),cost(trial)-cost(chosen),w['rank'],a,i,nw))
        if not options: break
        *_, i, nw = min(options,key=lambda x:x[:-1]); chosen[i]=nw
    payload = text(chosen) if chosen else '[PI D1 unknown no_window_fits]\n'
    ids = tokenizer.encode(payload,add_special_tokens=False)
    if len(ids)>budget: raise ValueError('explicit status does not fit')
    maps=[]
    for w in chosen:
        source=snapshot['files'][w['file']].splitlines(True)
        assert w['code']==''.join(source[w['start']-1:w['end']])
        maps.append(dict(entity_id=w['entity_id'],file=w['file'],qualified=w['qualified'],path_only_visible=False,
            source_hash=sha(w['code']),file_sha=sha(snapshot['files'][w['file']]),
            pi_emitted_source_spans_W0=[dict(line=n,start_column=0,end_column=len(source[n-1].rstrip('\r\n').encode()),line_complete=True) for n in range(w['start'],w['end']+1)]))
    return dict(pi_text=payload,pi_ids=ids,pi_raw_tokens=len(ids),token_cap=budget,pi_truncated=True,
        source_map=maps,windows=chosen,unknown=not chosen,omitted=not chosen,
        semantic_hash=digest([(w['file'],w['code']) for w in chosen]),
        source_lines=sum(w['end']-w['start']+1 for w in chosen),
        metadata_tokens_standalone=len(tokenizer.encode(text([dict(w,code='') for w in chosen]),add_special_tokens=False)),
        source_tokens_standalone=len(tokenizer.encode(''.join(w['code'] for w in chosen),add_special_tokens=False)))
