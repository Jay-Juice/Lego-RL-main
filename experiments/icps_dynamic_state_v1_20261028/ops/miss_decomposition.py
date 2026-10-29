"""Scorer-only development error analysis, aggregate export only."""
import ast,collections,gzip,json,pathlib,sys
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1];R=B/'experiments/pi_repair_state_v2_20261015'
sys.path[:0]=[str(N/'src'),str(N/'core')]
from window_serializer import query,terms
def read(p):return json.loads(p.read_text())
inputs={x['uid']:x for x in read(R/'.private_icps_v11_window_20261023/ISSUE_ONLY_INPUTS.json')}
audits={x['uid']:x for x in read(R/'.private_icps_bug_coverage_20261023/PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
rr=read(N/'.private_development_r2/PRIVATE_SCORED_ROWS.json')
counts=collections.Counter();dist=collections.Counter();types=collections.Counter()
for r in rr:
    m=r['metrics']['expand']['192']
    if not m.get('changed_selected_intersect_any') or m.get('changed_visible_intersect_any'):continue
    counts['missed_inside_candidate_pool']+=1;uid=r['uid'];a=audits[uid]
    d=read(N/'.private_development_r2'/f'{uid}.json');s=json.load(gzip.open(R/'.private_icps_bug_coverage_20261023/captures'/f'{uid}.json.gz','rt'))['snapshot']
    windows=d['serialized']['expand']['windows'];points=[(h['file'],n) for h in a['label_hunks'] for n in h['changed_lines'] if any(e['file']==h['file'] and e['start_line']<=n<=e['end_line'] for e in d['selected'])]
    distances=[min(abs(n-w['start']),abs(n-w['end'])) for p,n in points for w in windows if p==w['file']]
    if distances:
        gap=min(distances);dist['<=2' if gap<=2 else '<=5' if gap<=5 else '<=10' if gap<=10 else '<=20' if gap<=20 else '>20']+=1
    else:dist['no_target_file_window']+=1
    q,_=query(inputs[uid]['issue']);overlap=False;kinds=set()
    for p,n in points:
        lines=s['files'][p].splitlines();overlap|=bool(terms(lines[n-1])&q)
        try:tree=ast.parse(s['files'][p])
        except (SyntaxError,ValueError,RecursionError):kinds.add('parse_unavailable');continue
        nodes=[x for x in ast.walk(tree) if isinstance(x,ast.stmt) and x.lineno<=n<=x.end_lineno]
        if nodes:kinds.add(type(min(nodes,key=lambda x:x.end_lineno-x.lineno)).__name__)
        else:kinds.add('outside_statement')
    counts['target_line_has_issue_terms' if overlap else 'target_line_no_issue_terms']+=1
    types.update(kinds)
out=dict(method='expand',round='r2',all_development=True,counts=dict(counts),nearest_visible_distance_lines=dict(dist),target_statement_type_nonexclusive=dict(types),notes=['Labels used only in offline scorer. No per-task locations exported.','Distance is nearest window edge in the same file, not proof that expanding that window would fit.'])
with (N/'reports/MISSED_CANDIDATE_DECOMPOSITION_R2.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
