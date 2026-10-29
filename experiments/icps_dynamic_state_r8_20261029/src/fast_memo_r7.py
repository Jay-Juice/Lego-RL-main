"""Lossless per-invocation memoization of the frozen fast allocator.

No cache survives a source snapshot or crosses tasks. No runtime/global patch.
Acceptance requires byte-exact output replay, not higher heuristic scores.
"""
import functools,inspect,textwrap,types
from fast_allocation_r7 import candidate_order,ARMS
from window_research_r7 import serialize as original


def bind_order(term_function):
    return types.FunctionType(candidate_order.__code__,dict(candidate_order.__globals__,terms=term_function))


@functools.lru_cache(maxsize=2)
def compiled(cap,slots):
    from budget_ablation_r7 import clone_with_one_edit
    import dense_state,rank_windows_r6
    fallback=clone_with_one_edit(dense_state.serialize,'budget>192','budget>1024')
    old_fallback=clone_with_one_edit(rank_windows_r6.serialize,'budget <= 192','budget <= 1024',{'frozen_serialize':fallback})
    source=textwrap.dedent(inspect.getsource(original))
    edits={
        'not budget == 256':'budget not in (768,1024)',
        'while len(chosen) < 3:':'while len(chosen) < slots:',
        '    validate(snapshot)\n':'''    validate(snapshot)
    line_cache={};term_cache={}
    def file_lines(path):
        if path not in line_cache:line_cache[path]=snapshot['files'][path].splitlines(True)
        return line_cache[path]
    def cached_terms(value):
        if value not in term_cache:term_cache[value]=terms(value)
        return term_cache[value]
    local_order=bind_order(cached_terms)
''',
        'for order,w in enumerate(props):':'for order,w in local_order(props,chosen,seen,q,text,cost,tokenizer,budget,variant):',
        "features=terms(w['code'])&q":"features=cached_terms(w['code'])&q",
        "lines = snapshot['files'][w['file']].splitlines(True)":"lines = file_lines(w['file'])",
        "source=snapshot['files'][w['file']].splitlines(True)":"source=file_lines(w['file'])",
        "    while chosen and variant != 'compact3':\n        options = []":"    while chosen and variant != 'compact3':\n        options = []; current_cost=cost(chosen)",
        '                if cost(trial) > budget: continue':'                trial_cost=cost(trial)\n                if trial_cost > budget: continue',
        'options.append((-len(terms(line)&q),cost(trial)-cost(chosen),':'options.append((-len(cached_terms(line)&q),trial_cost-current_cost,',
    }
    for before,after in edits.items():
        assert source.count(before)==1,'reference source changed'
        source=source.replace(before,after)
    ns=dict(original.__globals__,slots=slots,bind_order=bind_order,experimental_serializer=lambda:old_fallback)
    exec(compile(source,'<R7-lossless-memo>','exec'),ns)
    return ns['serialize']


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ('fast768_8','fast1024_12'):raise ValueError('predeclared memo replay arm')
    cap,slots,_=ARMS[arm]
    return compiled(cap,slots)(candidates,snapshot,issue,tokenizer,budget=cap,variant='diverse6')
