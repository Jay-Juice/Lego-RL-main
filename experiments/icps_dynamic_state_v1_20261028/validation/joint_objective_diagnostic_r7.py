"""Post-score aggregate diagnostic; not a generator or a new PI selector.

Compare the rejected objective on real emitted windows, then count development
coverage losses. No per-case output, parameter changes or confirmation access.
"""
import collections
import gzip
import json
import sys
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
from joint_windows_r7 import Allocator

def main():
    O=N/'reports/joint_windows_r7';V=N/'.private_joint_windows_r7'
    ref=d.read(O/'GENERATION_RECEIPT.json');assert ref['count']==607
    aggregate=d.read(O/'AGGREGATE.json')
    assert aggregate['generation_receipt_SHA']==d.sha(O/'GENERATION_RECEIPT.json')
    scores={r['uid']:r for r in d.read(V/'PRIVATE_SCORED_ROWS.json')}
    issues={r['uid']:r['issue'] for r in d.read(d.V11/'ISSUE_ONLY_INPUTS.json')}
    counts={m:collections.Counter() for m in aggregate['matching_controls']}
    for item in ref['rows']:
        uid=item['uid'];p=V/f'{uid}.json';assert d.sha(p)==item['SHA'];v=d.read(p)
        cap=d.OLD/'captures'/f'{uid}.json.gz';assert d.sha(cap)==v['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot']
        alloc={k:Allocator(v['selected'][k],snapshot,issues[uid],None) for k in ('base6','symbols12')}
        for mode,control in aggregate['matching_controls'].items():
            pool,budget,_=aggregate['arms'][mode];a=alloc[pool]
            before=a.objective(v['serialized'][control]['windows']);after=a.objective(v['serialized'][mode]['windows'])
            sign='higher' if after>before+1e-9 else ('lower' if after<before-1e-9 else 'equal')
            c=counts[mode];c.update(tasks=1);c[sign]+=1
            old=scores[uid]['metrics'][control][str(budget)];new=scores[uid]['metrics'][mode][str(budget)]
            for field,label in [('changed_visible_intersect_any','visible'),('changed_visible_full_any','full')]:
                assert (field in old)==(field in new)
                if field not in old:
                    c['unavailable_'+label]+=1
                    continue
                c['evaluable_'+label]+=1
                if old[field] and not new[field]:c[sign+'_objective_lost_'+label]+=1
                if new[field] and not old[field]:c[sign+'_objective_gained_'+label]+=1
    for mode,c in counts.items():
        paired=aggregate['paired_vs_matching_control'][mode]
        for field,label in [('changed_visible_intersect_any','visible'),('changed_visible_full_any','full')]:
            assert c['evaluable_'+label]==paired[field]['n']==366
            assert sum(c[s+'_objective_lost_'+label] for s in ('higher','equal','lower'))==paired[field]['lost']
            assert sum(c[s+'_objective_gained_'+label] for s in ('higher','equal','lower'))==paired[field]['gained']
    d.save(O/'OBJECTIVE_DIAGNOSTIC.json',dict(UTC=d.utc(),status='POST_SCORE_DEVELOPMENT_DIAGNOSTIC_NOT_NEW_METHOD',
        counts={m:dict(c) for m,c in counts.items()},source_SHA=d.sha(Path(__file__)),
        joint_source_SHA=d.sha(N/'src/joint_windows_r7.py'),aggregate_SHA=d.sha(O/'AGGREGATE.json'),
        limitations=['Compares raw internal heuristic on same-task final windows, not comparable absolute semantic value across tasks.',
            'Higher-score/lower-coverage association diagnoses objective misalignment; does not prove which feature or search change caused it.',
            'Post-score aggregate development analysis; no per-case output, parameter tuning, confirmation or runtime use.']))
    print(json.dumps({m:dict(c) for m,c in counts.items()},indent=2),flush=True)

if __name__=='__main__':main()
