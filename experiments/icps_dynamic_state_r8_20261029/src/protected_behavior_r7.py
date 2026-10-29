"""Predeclared follow-up: protect original first1/2 seeds, then structural score.

No new weights, candidates or seeds. Protection is of selected seed windows;
later shared-budget context expansion can still change their final bounds.
"""
import inspect
import textwrap
from behavior_windows_r7 import prepare, signals
from window_research_r7 import serialize as original


def serialize(candidates,snapshot,issue,tokenizer,*,budget=256,protected=1):
    #3 is a source-contract identity control, not an evaluated new arm.
    if budget not in (256,384) or type(protected) is not int or protected not in (1,2,3):
        raise ValueError('predeclared protection only')
    props,adjusted,_=prepare(candidates,snapshot,issue,extend=False)
    source=textwrap.dedent(inspect.getsource(original))
    for before,after in {
        'not budget == 256':'budget not in (256,384)',
        "props = proposals(candidates, snapshot, issue, variant='flow_expand')":'props = fixed_props',
        "marginal_score(w['score'],features,seen,trial_cost-prior_cost,variant)":"marginal_score(w['score'] if len(chosen)<protected else adjusted(w),features,seen,trial_cost-prior_cost,variant)",
    }.items():
        assert source.count(before)==1;source=source.replace(before,after)
    ns=dict(original.__globals__,fixed_props=props,adjusted=adjusted,protected=protected)
    exec(compile(source,'<R7-protected-structural>','exec'),ns)
    return ns['serialize'](candidates,snapshot,issue,tokenizer,budget=budget,variant='diverse6')
