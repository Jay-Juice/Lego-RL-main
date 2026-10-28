"""Score the unchanged frozen nine-arm outputs; handle unscored rows explicitly."""
import importlib.util
import inspect
import sys
import textwrap
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
KEYS=('changed_visible_intersect_any','changed_visible_full_any','changed_visible_full_all')


def assert_retention(before,after):
    present={k for k in KEYS if k in before}
    assert present=={k for k in KEYS if k in after},'inconsistent eligibility'
    assert not present or present==set(KEYS),'incomplete target metrics'
    for k in present:
        assert type(before[k]) is bool and type(after[k]) is bool
        assert not before[k] or after[k],'append lost target evidence'


def main():
    import development as d
    spec=importlib.util.spec_from_file_location('capacity_frozen_driver',N/'validation/capacity_allocation_r7.py')
    run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
    old="""            for metric in ('changed_visible_intersect_any','changed_visible_full_any','changed_visible_full_all'):
                assert not before[metric] or after[metric], 'append lost target evidence'"""
    source=textwrap.dedent(inspect.getsource(run.score));assert source.count(old)==1
    source=source.replace(old,'            assert_retention(before,after)')
    ns=dict(run.score.__globals__,assert_retention=assert_retention)
    exec(compile(source,'<capacity-score-r2-eligibility-only>','exec'),ns)
    ns['score']()
    d.save(run.O/'SCORING_REPAIR.json',dict(status='SCORING_ONLY_ELIGIBILITY_FIX',UTC=d.utc(),
        prior_queue_exit=1,prior_error='KeyError on changed_visible_intersect_any for rows without mapped exact targets',
        generation_unchanged=True,scorer_wrapper_SHA=d.sha(Path(__file__)),
        original_scorer_SHA=d.sha(N/'validation/capacity_allocation_r7.py'),
        frozen_generation_receipt_SHA=d.sha(run.O/'GENERATION_RECEIPT.json'),aggregate_SHA=d.sha(run.O/'AGGREGATE.json')))


if __name__=='__main__':main()
