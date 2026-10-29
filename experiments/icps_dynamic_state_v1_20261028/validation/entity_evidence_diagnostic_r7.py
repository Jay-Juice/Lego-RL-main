"""Aggregate-only scorer after all outputs freeze. NEVER a PI constructor.

Separate entity-selection misses from within-entity localization misses.
No individual IDs, code, labels or suggestions are exported.
"""
import collections
import hashlib
import sys
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
import importlib.util
spec=importlib.util.spec_from_file_location('fast_study_driver',N/'validation/entity_evidence_r7.py')
run=importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def rank_band(rank):
    return '1-3' if rank<=3 else '4-6' if rank<=6 else '7-12' if rank<=12 else '13-24'


def main():
    receipt=d.read(run.O/'GENERATION_RECEIPT.json')
    agg=d.read(run.O/'AGGREGATE.json')
    assert receipt['source_SHA']==run.sources() and receipt['count']==607
    audit={r['uid']:r for r in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    prior={r['uid']:r for r in d.read(d.O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    buckets={m:collections.Counter() for m in run.ARMS}
    missed_ranks={m:collections.Counter() for m in run.ARMS}
    selected_ranks={m:collections.Counter() for m in run.ARMS}
    lengths=collections.Counter();first_hit_rank=collections.Counter()
    for row in receipt['rows']:
        uid=row['uid'];p=run.V/f'{uid}.json';assert d.sha(p)==row['SHA']
        meta=prior[uid]
        if meta['grade']!='exact_hunk' or meta['hunk_map_status']!='mapped':continue
        v=d.read(p);hunks=audit[uid]['label_hunks']
        target={(h['file'],i) for h in hunks for i in h['changed_lines']}
        candidates=v['selected']['passage24']
        relevant=[(i+1,e) for i,e in enumerate(candidates)
                  if any(e['file']==file and e['start_line']<=line<=e['end_line'] for file,line in target)]
        relevant_ids={e['entity_id'] for _,e in relevant}
        if relevant:
            first_hit_rank[rank_band(min(i for i,_ in relevant))]+=1
            size=min(e['end_line']-e['start_line']+1 for _,e in relevant)
            lengths['1-10' if size<=10 else '11-30' if size<=30 else '31-100' if size<=100 else '101+']+=1
        for mode in run.ARMS:
            z=v['serialized'][mode]
            visible={(e['file'],s['line']) for e in z['source_map'] for s in e['pi_emitted_source_spans_W0'] if s['line_complete']}
            buckets[mode]['tasks']+=1
            if target & visible:category='visible'
            elif not relevant:category='candidate_absent'
            elif any(w['entity_id'] in relevant_ids for w in z['windows']):category='target_entity_chosen_but_wrong_region'
            else:category='no_target_entity_chosen'
            buckets[mode][category]+=1
            if category not in ('visible','candidate_absent'):
                missed_ranks[mode][rank_band(min(i for i,_ in relevant))]+=1
            for rank in {w['rank']+1 for w in z['windows']}:
                selected_ranks[mode][rank_band(rank)]+=1
    for mode,b in buckets.items():
        assert b['tasks']==366
        assert sum(v for k,v in b.items() if k!='tasks')==366
        assert b['visible']==agg['results'][mode]['changed_visible_intersect_any']['hits']
        assert 366-b['candidate_absent']==343
    report=dict(status='SCORER_ONLY_AGGREGATE_LOSS_DECOMPOSITION',UTC=d.utc(),
        counts=buckets,missed_first_target_entity_rank=missed_ranks,
        final_distinct_candidate_rank_task_counts=selected_ranks,
        first_target_entity_rank=first_hit_rank,smallest_target_entity_source_lines=lengths,
        aggregate_SHA=d.sha(run.O/'AGGREGATE.json'),generation_receipt_SHA=d.sha(run.O/'GENERATION_RECEIPT.json'),
        source_SHA=d.sha(Path(__file__)),
        limitations=['Post-freeze label-informed diagnosis, not deployable selection.',
        'Target-overlapping entity may be a large enclosing class; rank bands are descriptive, not causal.',
        'No private per-case outputs exported. Reused development; no independent/RL claim.'])
    d.save(run.O/'LOSS_DECOMPOSITION.json',report)
    print(__import__('json').dumps(report,indent=2))


if __name__=='__main__':main()
