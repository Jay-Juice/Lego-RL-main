"""Scorer-only development diagnosis of redundant query signals."""
import collections,gzip,hashlib,json,pathlib,sys
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1]
R=B/'experiments/pi_repair_state_v2_20261015'
OLD=R/'.private_icps_bug_coverage_20261023';V=N/'.private_development_r4'
sys.path[:0]=[str(N/'src'),str(N/'core')]
from dense_state import proposals
from window_serializer import terms,query
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    f=read(N/'CANDIDATE_FREEZE_R4.json')
    for p,h in f['source_SHA'].items():assert sha(N/p)==h
    inputs={r['uid']:r['issue'] for r in read(R/'.private_icps_v11_window_20261023/ISSUE_ONLY_INPUTS.json')}
    rows=read(V/'PRIVATE_SCORED_ROWS.json');audit={r['uid']:r for r in read(OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    hashes={r['uid']:r['SHA'] for r in read(N/'reports/development_r4/GENERATION_RECEIPT.json')['rows']}
    out=collections.defaultdict(collections.Counter)
    for r in rows:
        old=r['metrics']['S1']['192'].get('changed_visible_intersect_any');new=r['metrics']['flow_expand']['192'].get('changed_visible_intersect_any')
        if old is None or new is None:continue
        candidate=r['metrics']['S1']['192']['changed_selected_intersect_any']
        group='lost' if old and not new else 'gained' if new and not old else 'both_hit' if old else 'both_miss_candidate' if candidate else 'outside_candidate'
        uid=r['uid'];p=V/f'{uid}.json';assert sha(p)==hashes[uid];d=read(p)
        cap=OLD/'captures'/f'{uid}.json.gz';assert sha(cap)==d['capture_SHA'];s=json.load(gzip.open(cap,'rt'))['snapshot']
        issue=inputs[uid];q,_=query(issue);ws=d['serialized']['flow_expand']['windows'];features=[terms(w['code'])&q for w in ws]
        c=out[group];c['cases']+=1;c['windows']+=len(ws)
        pairs=[len(a&b)/len(a|b) for i,a in enumerate(features) for b in features[i+1:] if a|b]
        c['any_query_jaccard_at_least_half']+=any(v>=.5 for v in pairs)
        seen=set()
        for fs in features:c['windows_without_new_query_terms']+=bool(fs) and not bool(fs-seen);seen|=fs
        target={(h['file'],n) for h in audit[uid]['label_hunks'] for n in h['changed_lines']}
        hitprops=[w for w in proposals(d['selected'],s,issue,variant='flow_expand') if any(w['file']==f and w['start']<=n<=w['end'] for f,n in target)]
        c['target_proposal_has_unseen_query_term']+=any((terms(w['code'])&q)-seen for w in hitprops)
        c['target_proposal_has_any_query_term']+=any(terms(w['code'])&q for w in hitprops)
    assert sum(g['cases'] for g in out.values())==366
    result=dict(status='DEVELOPMENT_ONLY',groups=dict(out),confirmation_read=False,selector_changed=False,
        source_SHA=f['source_SHA'],script_SHA=sha(pathlib.Path(__file__)),
        limitations=['Query-set overlap is a proxy, not causal importance or semantic equivalence.',
        'Target-proposal attribution reads labels in scorer only. No labels supplied to generator.'])
    with (N/'reports/R6_SIGNAL_AUDIT.json').open('x') as p:json.dump(result,p,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
