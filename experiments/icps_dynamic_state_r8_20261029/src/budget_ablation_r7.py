"""Development-only factorial. Frozen modules and runtime are never modified."""
import inspect
import textwrap
from functools import lru_cache
import rank_windows_r6 as r6
import dense_state
import issue_program_state as index


def clone_with_one_edit(function, before, after, overrides=None):
    source = textwrap.dedent(inspect.getsource(function))
    assert source.count(before) == 1, 'reference source changed'
    namespace = dict(function.__globals__)
    namespace.update(overrides or {})
    exec(compile(source.replace(before, after), '<R7-development-only>', 'exec'), namespace)
    return namespace[function.__name__]


@lru_cache(maxsize=1)
def experimental_serializer():
    fallback = clone_with_one_edit(dense_state.serialize, 'budget>192', 'budget>384')
    return clone_with_one_edit(r6.serialize, 'budget <= 192', 'budget <= 384',
                               {'frozen_serialize': fallback})


@lru_cache(maxsize=1)
def six_candidate_index():
    return clone_with_one_edit(index.build_initial_index, 'selected=ranked[:3]',
                               'selected=ranked[:6]')


def serialize(candidates, snapshot, issue, tokenizer, *, budget):
    if budget not in (192, 256, 384):
        raise ValueError('predeclared W0 ablation budgets only')
    return experimental_serializer()(candidates, snapshot, issue, tokenizer,
                                    budget=budget, variant='novelty_cost_expand')
