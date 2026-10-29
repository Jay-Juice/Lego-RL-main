"""Development-only entity evidence and exact cached/batched construction.

No retrieval, model, labels or persistent cache. Query evidence describes an
entire candidate, not proof that the evidence is present in a chosen window.
"""
import ast
import collections
import functools
import inspect
import math
import textwrap
import types
import executable_windows
from behavior_windows_r7 import own_nodes
from dense_state import validate
from fast_allocation_r7 import MeteredCache as BaseCache, compiled as baseline_compiled
from fast_allocation_r7 import candidate_order
from window_research_r7 import serialize as original
from window_serializer import resolve, query, terms

ARMS={m:(1024,8) for m in ('control1024_8','cached1024_8','entity1024_8','complement1024_8')}


class MeteredCache(BaseCache):
    def __init__(self,tokenizer):
        super().__init__(tokenizer);self.backend_batches=0
    def prefetch(self,texts):
        missing=list(dict.fromkeys(t for t in texts if t not in self.cache))
        if not missing:return
        if not callable(self.tokenizer):
            for t in missing:self.encode(t,add_special_tokens=False)
            return
        ids=self.tokenizer(missing,add_special_tokens=False,padding=False,truncation=False,
                           return_attention_mask=False,return_token_type_ids=False)['input_ids']
        assert len(ids)==len(missing)
        self.backend_batches+=1
        for t,values in zip(missing,ids):
            self.cache[t]=tuple(values);self.misses+=1;self.encoded_bytes+=len(t.encode())
    def stats(self):return dict(super().stats(),backend_batches=self.backend_batches)


def evidence(entities,issue):
    q,explicit=query(issue);docs={};names=collections.defaultdict(list)
    for e in entities:
        if not e['available']:continue
        root=e.get('node');words=terms(e['file']+' '+e['qualified'])
        nodes=list(own_nodes(root)) if root is not None else []
        doclines={n.value.lineno for n in nodes if isinstance(n,ast.Expr)
                  and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)}
        for n in nodes:
            value=None
            if isinstance(n,ast.Name):value=n.id
            elif isinstance(n,ast.Attribute):value=n.attr
            elif isinstance(n,ast.arg):value=n.arg
            elif isinstance(n,ast.Constant) and isinstance(n.value,str) and n.lineno not in doclines:value=n.value
            if value:words|=terms(value)
        docs[e['entity_id']]=words&q
        names[e['qualified'].lower().rsplit('.',1)[-1]].append(e['entity_id'])
    df=collections.Counter(t for doc in docs.values() for t in doc)
    weight={t:math.log1p((len(docs)+1)/(df[t]+1)) for t in sorted(q)}
    support={eid:sum(weight[t] for t in sorted(doc)) for eid,doc in docs.items()}
    scale=max(support.values(),default=0) or 1
    exact={ids[0] for name,ids in names.items() if len(ids)==1 and name in explicit}
    return docs,weight,{eid:s/scale for eid,s in support.items()},exact,scale


@functools.lru_cache(maxsize=1)
def template():
    s=textwrap.dedent(inspect.getsource(original))
    edits={
        'not budget == 256':'budget != 1024',
        'while len(chosen) < 3:':'while len(chosen) < 8:',
        'for order,w in enumerate(props):':'for order,w in local_order(props,chosen,seen,q,text,cost,tokenizer,budget,variant):',
        "features=terms(w['code'])&q":"features=cached_terms(w['code'])&q",
        "utility /= math.sqrt(1+w['rank'])":"utility /= math.sqrt(1+w['rank'])\n                utility *= factor(w,chosen)",
        "lines = snapshot['files'][w['file']].splitlines(True)":"lines = file_lines(w['file'])",
        "source=snapshot['files'][w['file']].splitlines(True)":"source=file_lines(w['file'])",
        "    while chosen and variant != 'compact3':\n        options = []":"    while chosen and variant != 'compact3':\n        prefetch_expansions(chosen,current,text,cost,tokenizer)\n        options = []; current_cost=cost(chosen)",
        '                if cost(trial) > budget: continue':'                trial_cost=cost(trial)\n                if trial_cost > budget: continue',
        'options.append((-len(terms(line)&q),cost(trial)-cost(chosen),':'options.append((-len(cached_terms(line)&q),trial_cost-current_cost,',
    }
    for before,after in edits.items():
        assert s.count(before)==1,'reference changed';s=s.replace(before,after)
    return compile(s,'<R7-entity-evidence>','exec')


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ARMS:raise ValueError('predeclared evidence arm')
    if arm=='control1024_8':
        return baseline_compiled(1024,8)(candidates,snapshot,issue,tokenizer,budget=1024,variant='diverse6')
    validate(snapshot)
    if not hasattr(tokenizer,'prefetch'):tokenizer=MeteredCache(tokenizer)
    entities=resolve(candidates,snapshot['files']);line_cache={};term_cache={};factor_cache={}
    def file_lines(path):
        if path not in line_cache:line_cache[path]=snapshot['files'][path].splitlines(True)
        return line_cache[path]
    def cached_terms(value):
        if value not in term_cache:term_cache[value]=terms(value)
        return term_cache[value]
    def local_resolve(*args):return entities
    docs,weights,support,exact,scale=evidence(entities,issue) if arm!='cached1024_8' else ({},{},{},set(),1)
    def factor(w,chosen):
        if arm=='cached1024_8':return 1
        key=tuple(x['entity_id'] for x in chosen)
        if key not in factor_cache:
            seen=set().union(*(docs.get(eid,set()) for eid in key))
            factors={}
            for eid,doc in docs.items():
                novelty=sum(weights[t] for t in sorted(doc-seen))/scale if arm=='complement1024_8' else 0
                factors[eid]=1+.5*support[eid]+.25*(eid in exact)+.25*novelty
                assert 1<=factors[eid]<=2.00000001
            factor_cache[key]=factors
        return factor_cache[key].get(w['entity_id'],1)
    signals=types.FunctionType(executable_windows.line_signals.__code__,
        dict(executable_windows.line_signals.__globals__,terms=cached_terms))
    make_props=types.FunctionType(executable_windows.proposals.__code__,
        dict(executable_windows.proposals.__globals__,resolve=local_resolve,line_signals=signals))
    def local_props(c,s,i,variant):
        assert variant=='flow_expand'
        rows=[dict(w,changed_lines=0,unit='context') for w in make_props(c,s['files'],i,flow=True)]
        return sorted(rows,key=lambda w:(-int(w['changed_lines']>0),-w['score'],w['rank'],w['file'],w['start'],-(w['end']-w['start'])))
    order_source=textwrap.dedent(inspect.getsource(candidate_order))
    before="        utility/=math.sqrt(1+w['rank'])"
    assert order_source.count(before)==1
    order_source=order_source.replace(before,before+'\n        utility*=factor(w,chosen)')
    before="        feasible=[(order,w) for _,order,w in chunk if cost(chosen+[w])<=budget]"
    assert order_source.count(before)==1
    order_source=order_source.replace(before,"        tokenizer.prefetch([text(chosen+[w]) for _,_,w in chunk])\n"+before)
    order_ns=dict(candidate_order.__globals__,terms=cached_terms,factor=factor)
    exec(compile(order_source,'<R7-local-order>','exec'),order_ns)
    def prefetch_expansions(chosen,current,text,cost,tok):
        payloads=[]
        for i,w in enumerate(chosen):
            e=current[w['entity_id']];lines=file_lines(w['file'])
            for a,b in ((w['start']-1,w['end']),(w['start'],w['end']+1)):
                if a<e['start_line'] or b>e['end_line']:continue
                if any(j!=i and x['file']==w['file'] and max(a,x['start'])<=min(b,x['end']) for j,x in enumerate(chosen)):continue
                nw=dict(w,start=a,end=b,code=''.join(lines[a-1:b]))
                payloads.append(text(chosen[:i]+[nw]+chosen[i+1:]))
        tok.prefetch(payloads)
    from budget_ablation_r7 import clone_with_one_edit
    import dense_state,rank_windows_r6
    fallback=clone_with_one_edit(dense_state.serialize,'budget>192','budget>1024')
    old_fallback=clone_with_one_edit(rank_windows_r6.serialize,'budget <= 192','budget <= 1024',{'frozen_serialize':fallback})
    ns=dict(original.__globals__,resolve=local_resolve,proposals=local_props,cached_terms=cached_terms,
            file_lines=file_lines,factor=factor,local_order=order_ns['candidate_order'],
            prefetch_expansions=prefetch_expansions,experimental_serializer=lambda:old_fallback)
    exec(template(),ns)
    return ns['serialize'](candidates,snapshot,issue,tokenizer,budget=1024,variant='diverse6')
