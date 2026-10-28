"""Post-freeze scorer-only window feasibility witnesses; never a PI generator."""
import collections
import gzip
import json
import sys
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
from dense_state import proposals,render


def main():
    V=N/'.private_recall_windows_r7_r2';O=N/'reports/recall_windows_r7_r2'
    ref=d.read(O/'GENERATION_RECEIPT.json');aggregate=d.read(O/'AGGREGATE.json')
    assert ref['count']==607 and aggregate['generation_receipt_SHA']==d.sha(O/'GENERATION_RECEIPT.json')
    scores={r['uid']:r for r in d.read(V/'PRIVATE_SCORED_ROWS.json')}
    audits={r['uid']:r for r in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    issues={r['uid']:r['issue'] for r in d.read(d.V11/'ISSUE_ONLY_INPUTS.json')}
    ARMS=aggregate['arms']
    tok=d.tokenizer();counts={mode:collections.Counter() for mode in ARMS}
    for item in ref['rows']:
        uid=item['uid'];row=scores[uid]
        if 'changed_visible_intersect_any' not in row['metrics']['base12_256']['256']:continue
        p=V/f'{uid}.json';assert d.sha(p)==item['SHA'];v=d.read(p)
        cap=d.OLD/'captures'/f'{uid}.json.gz';assert d.sha(cap)==v['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot']
        want={(h['file'],line) for h in audits[uid]['label_hunks'] for line in h['changed_lines']}
        hit_costs={}
        for pool in {pool for pool,_ in ARMS.values()}:
            pp=proposals(v['selected'][pool],snapshot,issues[uid],variant='flow_expand')
            pp=[w for w in pp if any(w['file']==path and w['start']<=line<=w['end'] for path,line in want)]
            hit_costs[pool]=[len(tok.encode(render([w],snapshot.get('limited',False)),add_special_tokens=False)) for w in pp]
        for mode,(pool,budget) in ARMS.items():
            m=row['metrics'][mode][str(budget)];c=counts[mode];c['tasks']+=1
            hit=m['changed_visible_intersect_any'];candidate=m['changed_selected_intersect_any']
            costs=hit_costs[pool];fits=any(cost<=budget for cost in costs)
            if hit:c['already_visible']+=1
            elif not candidate:c['candidate_missing']+=1
            elif not costs:c['candidate_present_but_no_seed_proposal_hits']+=1
            elif not fits:c['hitting_seed_proposals_all_over_budget_alone']+=1
            else:c['fitting_hitting_seed_exists_but_not_selected']+=1
            if hit or fits:c['actual_or_single_seed_attainability_witness']+=1
    categories=['already_visible','candidate_missing','candidate_present_but_no_seed_proposal_hits',
                'hitting_seed_proposals_all_over_budget_alone','fitting_hitting_seed_exists_but_not_selected']
    for mode,c in counts.items():
        assert c['tasks']==sum(c[x] for x in categories)==366
        assert c['already_visible']==aggregate['results'][mode]['changed_visible_intersect_any']['hits']
    result=dict(UTC=d.utc(),status='SCORER_ONLY_FIXED_PROPOSAL_DIAGNOSTIC_NOT_DEPLOYABLE',counts=counts,
        aggregate_SHA=d.sha(O/'AGGREGATE.json'),source_SHA=d.sha(Path(__file__)),
        limitations=['Labels only after frozen generation and main scoring; never used to select deployed PI.',
        'A one-window target-hit witness fits the real token cap and max3/nonoverlap constraints, but does not establish semantic completeness.',
        'Fixed seed proposals exclude later residual expansion alternatives; this is not a global optimum or an upper bound over all possible source windows.',
        'Categories describe a fixed pipeline, not causal proof about individual features. No case IDs or scores exported.'])
    d.save(O/'WINDOW_BOTTLENECKS.json',result)
    print(json.dumps(counts,indent=2),flush=True)

if __name__=='__main__':main()
