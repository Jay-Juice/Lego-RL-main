"""Development-only V2-budget ablation; copied frozen fast allocator, caps only; no neural retrieval or label access.

Approximate only candidate ordering with independently tokenized window bodies.
Actual full-payload tokenization remains authoritative for every selected seed,
every context expansion and final output. Same source proposals/rank prior.
"""
import functools
import inspect
import math
import textwrap
from capacity_allocation_r7 import TokenCache, serialize as reference
from window_research_r7 import serialize as original, marginal_score
from window_serializer import terms
from dense_state import overlap

ARMS = {'control1024_8':(1024,8,True),'fast1920_8':(1920,8,True),'fast2048_8':(2048,8,True)}
SHORTLIST=8


class MeteredCache(TokenCache):
    """Fresh per arm/task; never shared between benchmark arms."""
    def __init__(self,tokenizer):
        super().__init__(tokenizer)
        self.requests=0;self.misses=0;self.encoded_bytes=0
    def encode(self,text,*,add_special_tokens=False):
        self.requests+=1
        if text not in self.cache:
            self.misses+=1;self.encoded_bytes+=len(text.encode())
        return super().encode(text,add_special_tokens=add_special_tokens)
    def stats(self):
        return dict(encode_requests=self.requests,encode_misses=self.misses,encoded_bytes=self.encoded_bytes)


def candidate_order(props,chosen,seen,q,text,cost,tokenizer,budget,variant):
    header=text([]); ranked=[]
    for order,w in enumerate(props):
        if any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in chosen):continue
        body=text([w])[len(header):]
        if chosen and chosen[-1]['file']==w['file']:
            assert body.startswith(w['file']+':')
            body=body[len(w['file']):]
        estimate=max(1,len(tokenizer.encode(body,add_special_tokens=False)))
        features=terms(w['code'])&q
        utility=marginal_score(w['score'],features,seen,estimate,variant)
        utility/=math.sqrt(1+w['rank'])
        utility/=1+sum(x['entity_id']==w['entity_id'] for x in chosen)
        ranked.append((-utility,order,w))
    ranked.sort(key=lambda x:x[:2])
    # Do not reject from an approximate cost. If a chunk has no fitting window,
    # inspect the next chunk; exhausted search keeps the explicit empty fallback.
    for start in range(0,len(ranked),SHORTLIST):
        chunk=ranked[start:start+SHORTLIST]
        feasible=[(order,w) for _,order,w in chunk if cost(chosen+[w])<=budget]
        if feasible:
            return feasible
    return []


@functools.lru_cache(maxsize=6)
def compiled(budget,slots):
    from budget_ablation_r7 import clone_with_one_edit
    import dense_state,rank_windows_r6
    fallback=clone_with_one_edit(dense_state.serialize,'budget>192','budget>2048')
    old_fallback=clone_with_one_edit(rank_windows_r6.serialize,'budget <= 192','budget <= 2048',{'frozen_serialize':fallback})
    source=textwrap.dedent(inspect.getsource(original))
    edits={
        'not budget == 256':'budget not in (1024,1920,2048)',
        'while len(chosen) < 3:':'while len(chosen) < slots:',
        'for order,w in enumerate(props):':'for order,w in candidate_order(props,chosen,seen,q,text,cost,tokenizer,budget,variant):',
    }
    for before,after in edits.items():
        assert source.count(before)==1,'reference source changed'
        source=source.replace(before,after)
    ns=dict(original.__globals__,slots=slots,candidate_order=candidate_order,experimental_serializer=lambda:old_fallback)
    exec(compile(source,'<R7-fast-allocation>','exec'),ns)
    return ns['serialize']


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ARMS:raise ValueError('predeclared fast allocation arm')
    cap,slots,fast=ARMS[arm]
    if arm=='control1024_8':
        from fast_allocation_r7 import serialize as baseline
        return baseline(candidates,snapshot,issue,tokenizer,arm='fast1024_8')
    return compiled(cap,slots)(candidates,snapshot,issue,tokenizer,budget=cap,variant='diverse6')
