"""Post-generation scorer-only density and exact control audit; no PI writes."""
import collections
import hashlib
import json
import pathlib

N=pathlib.Path(__file__).resolve().parents[1]
R=N.parent/'pi_repair_state_v2_20261015'
OLD=R/'.private_icps_bug_coverage_20261023'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=read(N/'reports/development_r4/GENERATION_RECEIPT.json')
aggregate=read(N/'reports/development_r4/AGGREGATE.json')
audit={x['uid']:x for x in read(OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
prior={x['uid']:x for x in read(R/'logs/icps_v11_window_20261023/ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
stats=collections.defaultdict(collections.Counter)
control_equal=0
for ref in receipt['rows']:
    uid=ref['uid'];p=N/'.private_development_r4'/f'{uid}.json'
    assert sha(p)==ref['SHA']
    d=read(p)
    previous=read(N/'.private_development_r3'/f'{uid}.json')
    assert d['serialized']['expand']==previous['serialized']['expand']
    control_equal+=1
    exact=prior[uid]['grade']=='exact_hunk' and prior[uid]['hunk_map_status']=='mapped'
    target={(h['file'],n) for h in audit[uid]['label_hunks'] for n in h['changed_lines']} if exact else set()
    for mode,z in d['serialized'].items():
        s=stats[mode];s['cases']+=1;s['actual_PI_tokens']+=len(z['pi_ids'])
        s['source_tokens_standalone']+=z['source_tokens_standalone']
        s['metadata_tokens_standalone']+=z['metadata_tokens_standalone']
        visible={(m['file'],span['line']) for m in z['source_map'] for span in m['pi_emitted_source_spans_W0'] if span['line_complete']}
        s['unique_visible_lines']+=len(visible)
        if exact:
            s['evaluable']+=1;s['evaluable_actual_tokens']+=len(z['pi_ids'])
            s['visible_target_lines_or_anchors']+=len(visible&target)
            s['all_target_lines_or_anchors']+=len(target)
for mode,s in stats.items():
    s['target_lines_per_1000_actual_tokens']=1000*s['visible_target_lines_or_anchors']/max(1,s['evaluable_actual_tokens'])
    s['source_standalone_per_actual_token_proxy']=s['source_tokens_standalone']/max(1,s['actual_PI_tokens'])
    s['case_target_hits_per_1000_actual_tokens']=1000*aggregate['results'][mode]['changed_visible_intersect_any']['hits']/max(1,s['evaluable_actual_tokens'])
out=dict(control_R3_expand_exact_equal_cases=control_equal,statistics=dict(stats),
    limitations=['Scorer-only label coordinates; never used by the generator.',
    'Standalone source and metadata tokenization is non-additive; ratios are proxies, not exact attribution.',
    'Target-line density is a coverage surrogate, not measured value-prediction information or generalization.',
    'All 607 cases are development. Zero-width deletion anchors count as existing source anchors.'])
assert control_equal==607
with (N/'reports/DENSITY_CONTROL_R4.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
