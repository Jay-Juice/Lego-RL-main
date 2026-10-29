"""Single-factor development follow-up: preserve old objective/proposals/context.

Only greedy selection becomes width4 lookahead. Retains the exact greedy path
as an incumbent. Uses original rendered token costs and ordering, no target IO.
"""
import copy
import inspect
import math
import textwrap
from functools import lru_cache
from window_research_r7 import serialize as old_serialize, marginal_score
from window_serializer import terms
from dense_state import overlap

WIDTH=4

def choose(props,cost,budget,q):
    order={id(w):i for i,w in enumerate(props)};cache={}
    def key(ws):return tuple(order[id(w)] for w in ws)
    def tokens(ws):
        k=key(ws)
        if k not in cache:cache[k]=cost(ws)
        return cache[k]
    # state: windows, sum of ORIGINAL sequential marginal utilities, seen terms
    beam=[([],0.,set())];finalists=list(beam);greedy=()
    sortkey=lambda s:(-s[1],key(s[0]))
    for depth in range(3):
        children=[];incumbent=None
        for ws,total,seen in beam:
            opts=[];prior_cost=tokens(ws)
            for i,w in enumerate(props):
                if any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in ws):continue
                used=tokens(ws+[w])
                if used>budget:continue
                features=terms(w['code'])&q
                utility=marginal_score(w['score'],features,seen,used-prior_cost,'diverse6')
                utility/=math.sqrt(1+w['rank'])
                utility/=1+sum(x['entity_id']==w['entity_id'] for x in ws)
                opts.append((-utility,i,w,features))
            opts.sort(key=lambda x:x[:2])
            for position,(negative,_,w,features) in enumerate(opts[:WIDTH]):
                state=(ws+[w],total-negative,seen|features);children.append(state)
                if key(ws)==greedy and position==0:incumbent=state
        if not children:break
        finalists.extend(children)
        beam=sorted(children,key=sortkey)[:WIDTH]
        if incumbent is not None:
            greedy=key(incumbent[0])
            if all(key(s[0])!=greedy for s in beam):beam=beam[:WIDTH-1]+[incumbent]
    return copy.deepcopy(min(finalists,key=sortkey)[0])


@lru_cache(maxsize=1)
def serializer():
    source=textwrap.dedent(inspect.getsource(old_serialize))
    start=source.index('    while len(chosen) < 3:')
    end=source.index('    if not chosen:',start)
    block=source[start:end]
    assert 'chosen.append(copy.deepcopy(w));seen|=features' in block
    assert source.count('not budget == 256')==1 and source.count(block)==1
    source=source.replace(block,'    chosen = lookahead_choose(props, cost, budget, q)\n')
    source=source.replace('not budget == 256','budget not in (256,384)')
    namespace=dict(old_serialize.__globals__);namespace['lookahead_choose']=choose
    exec(compile(source,'<R7-lookahead-selection-only>','exec'),namespace)
    return namespace['serialize']


def serialize(candidates,snapshot,issue,tokenizer,*,budget=256):
    return serializer()(candidates,snapshot,issue,tokenizer,budget=budget,variant='diverse6')
