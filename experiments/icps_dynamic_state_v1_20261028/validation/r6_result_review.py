"""Post-selection descriptive audit; original607 development only, no generation."""
import collections, hashlib, json, pathlib, sys
N=pathlib.Path(__file__).resolve().parents[1]; B=N.parents[1]
R=B/'experiments/pi_repair_state_v2_20261015'
V=N/'.private_development_r6'; O=N/'reports/development_r6'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    sys.path.insert(0,str(R/'ops/icps_bug_coverage_20261023'))
    from evaluate import paired
    rows=read(V/'PRIVATE_SCORED_ROWS.json')
    receipt=read(O/'GENERATION_RECEIPT.json')
    assert len(rows)==receipt['count']==607
    frozen=read(O/'FROZEN.json')
    for path,h in frozen['source_SHA'].items(): assert sha(N/path)==h
    audit={r['uid']:r for r in read(R/'.private_icps_bug_coverage_20261023/PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    modes=['S1','flow_expand','novelty_expand','novelty_cost_expand']
    stats={m:collections.Counter() for m in modes}
    hashes={r['uid']:r['SHA'] for r in receipt['rows']}
    comparisons={}
    for m in modes[2:]:
        pr=[dict(r,metrics={'R0':r['metrics']['flow_expand'],'R1':r['metrics'][m]}) for r in rows]
        comparisons[m]={k:paired(pr,192,k) for k in ['changed_visible_intersect_any','changed_visible_full_any']}
    for r in rows:
        if r['metrics']['S1']['192'].get('changed_visible_intersect_any') is None: continue
        uid=r['uid']; p=V/f'{uid}.json'; assert sha(p)==hashes[uid];d=read(p)
        target={(h['file'],n) for h in audit[uid]['label_hunks'] for n in h['changed_lines']}
        for m in modes:
            z=d['serialized'][m]; visible={(x['file'],v['line']) for x in z['source_map'] for v in x.get('pi_emitted_source_spans_W0',[])}
            s=stats[m];s['cases']+=1;s['actual_tokens']+=len(z['pi_ids'])
            s['target_lines_total']+=len(target);s['target_lines_visible']+=len(visible & target)
            s['visible_lines']+=len(visible)
    for s in stats.values():
        assert s['cases']==366
        s['target_lines_per_1000_actual_tokens']=1000*s['target_lines_visible']/s['actual_tokens']
    result=dict(status='POST_SELECTION_DESCRIPTIVE_DEVELOPMENT_ONLY',comparison_against_R4=comparisons,density=stats,
        receipt_SHA=sha(O/'GENERATION_RECEIPT.json'),source_SHA=frozen['source_SHA'],script_SHA=sha(pathlib.Path(__file__)),
        confirmation_read=False,selector_changed=False,GPU_jobs=0,optimizer_steps=0,
        limitations=['R6 minus R4 is exploratory after observing development; intervals are not independent confirmation.',
                     'Target-line density is a source coverage proxy, not Critic utility or RL improvement.',
                     'All607 are development. No new validation tasks were consumed.'])
    with (N/'reports/R6_RESULT_REVIEW.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
