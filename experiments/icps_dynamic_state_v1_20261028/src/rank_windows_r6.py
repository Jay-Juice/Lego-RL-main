"""W0 marginal-query allocators. Pure current source; no IO or labels."""
import copy
from window_serializer import resolve, query, terms, sha, digest
from dense_state import validate, proposals, render, overlap, serialize as frozen_serialize

VARIANTS = ('novelty_expand', 'novelty_cost_expand')

def marginal_score(score, features, seen, marginal_cost, variant):
    repeated=len(features & seen)/max(1,len(features))
    utility=score/(1+repeated)
    if variant=='novelty_cost_expand': utility/=max(1,marginal_cost)**.5
    return utility

def serialize(candidates, snapshot, issue, tokenizer, *, budget=192, variant='novelty_expand'):
    if variant not in VARIANTS or not 0 <= budget <= 192:
        raise ValueError('prototype variant/budget')
    validate(snapshot)
    chosen = []
    def text(ws): return render(ws, snapshot.get('limited', False))
    def cost(ws): return len(tokenizer.encode(text(ws), add_special_tokens=False))
    props = proposals(candidates, snapshot, issue, variant='flow_expand')
    q, _ = query(issue); seen = set()
    while len(chosen) < 3:
        opts=[]; prior_cost=cost(chosen)
        for order,w in enumerate(props):
            if any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in chosen):continue
            trial_cost=cost(chosen+[w])
            if trial_cost>budget:continue
            features=terms(w['code'])&q
            utility=marginal_score(w['score'],features,seen,trial_cost-prior_cost,variant)
            opts.append((-utility,order,w,features))
        if not opts:break
        _,_,w,features=min(opts,key=lambda x:x[:2]);chosen.append(copy.deepcopy(w));seen|=features
    if not chosen:
        return frozen_serialize(candidates,snapshot,issue,tokenizer,budget=budget,variant='flow_expand')
    current = {e['entity_id']: e for e in resolve(candidates, snapshot['files'])}
    q, _ = query(issue)
    while chosen:
        options = []
        for i, w in enumerate(chosen):
            e = current[w['entity_id']]; lines = snapshot['files'][w['file']].splitlines(True)
            for a, b in [(w['start']-1, w['end']), (w['start'], w['end']+1)]:
                if a < e['start_line'] or b > e['end_line']: continue
                if any(j != i and x['file'] == w['file'] and overlap((a,b),(x['start'],x['end'])) for j,x in enumerate(chosen)): continue
                code = ''.join(lines[a-1:b])
                nw = dict(w,start=a,end=b,code=code,source_hash=sha(code),partial=a!=e['start_line'] or b!=e['end_line'])
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
