"""Fixed512/6 source-only causal ablations of rank prior and entity repetition.

This is not a semantic reranker. No weights learned from case scores. The original
proposal bank, marginal cost/novelty score and context expansion are unchanged.
"""
import inspect
import math
import textwrap
from window_research_r7 import serialize as original
from capacity_allocation_r7 import TokenCache

ARMS = ('control512','flat512','unique512','unique_flat512','anchor2_flat512')


def priority(rank, chosen_count, arm):
    if arm not in ARMS:raise ValueError('predeclared entity allocation arm')
    exponent=.5 if arm in ('control512','unique512') or (arm=='anchor2_flat512' and chosen_count<2) else 0
    return math.sqrt(1+rank) if exponent==.5 else 1.0


def tier(window,chosen,arm):
    return int(arm in ('unique512','unique_flat512') and any(w['entity_id']==window['entity_id'] for w in chosen))


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ARMS:raise ValueError('predeclared entity allocation arm')
    source=textwrap.dedent(inspect.getsource(original))
    edits={
        'not budget == 256':'budget != 512',
        'while len(chosen) < 3:':'while len(chosen) < 6:',
        "utility /= math.sqrt(1+w['rank'])":"utility /= prior(w['rank'],len(chosen))",
        'opts.append((-utility,order,w,features))':'opts.append((entity_tier(w,chosen),-utility,order,w,features))',
        "_,_,w,features=min(opts,key=lambda x:x[:2])":"_,_,_,w,features=min(opts,key=lambda x:x[:3])",
    }
    for before,after in edits.items():
        assert source.count(before)==1,'reference changed'
        source=source.replace(before,after)
    # Empty/oversize source fallback: use the already tested cap512 control,
    # preserving source-only behavior without touching any frozen module.
    from budget_ablation_r7 import clone_with_one_edit
    import dense_state,rank_windows_r6
    fallback=clone_with_one_edit(dense_state.serialize,'budget>192','budget>512')
    old_fallback=clone_with_one_edit(rank_windows_r6.serialize,'budget <= 192','budget <= 512',{'frozen_serialize':fallback})
    ns=dict(original.__globals__,prior=lambda rank,n:priority(rank,n,arm),
            entity_tier=lambda w,chosen:tier(w,chosen,arm),experimental_serializer=lambda:old_fallback)
    exec(compile(source,'<R7-entity-allocation>','exec'),ns)
    return ns['serialize'](candidates,snapshot,issue,tokenizer,budget=512,variant='diverse6')
