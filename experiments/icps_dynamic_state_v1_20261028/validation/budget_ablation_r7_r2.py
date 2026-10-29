"""607 development inputs only; label-denied generation, separate scoring."""
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

N = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(N/'src'), str(N/'core'), str(N/'validation')]
import development as d
from budget_ablation_r7 import serialize, six_candidate_index

ARMS = [(k,b) for k in (3,6) for b in (192,256,384)]
V = N/'.private_budget_ablation_r7_r2'
O = N/'reports/budget_ablation_r7_r2'
BASE = N/'.private_development_r6'
def name(k,b): return f'k{k}_b{b}'
def inputs_sha():
    files = ['src/budget_ablation_r7.py','validation/budget_ablation_r7_r2.py',
             'validation/development.py','validation/landlock.py','R7_BUDGET_ABLATION_R2_PLAN.md']
    files += list(d.read(N/'CANDIDATE_FREEZE_R6_SESSION.json')['source_SHA'])
    return {f:d.sha(N/f) for f in files}


def generate(shard):
    os.umask(0o077); assert V.is_dir() and O.is_dir()
    assert shard in range(4)
    tok=d.tokenizer(); reference=d.read(N/'reports/development_r6/GENERATION_RECEIPT.json')
    basehash={r['uid']:r['SHA'] for r in reference['rows']}
    rows=sorted(d.read(d.V11/'ISSUE_ONLY_INPUTS.json'),key=lambda r:r['uid'])
    assert len(rows)==len(basehash)==607
    sources=inputs_sha()
    for f,h in d.read(N/'CANDIDATE_FREEZE_R6_SESSION.json')['source_SHA'].items(): assert d.sha(N/f)==h
    if shard == 0: d.save(O/'FROZEN.json',dict(UTC=d.utc(),arms=ARMS,source_SHA=sources,all607_development=True,
           input_SHA=d.sha(d.V11/'ISSUE_ONLY_INPUTS.json'),confirmation_used=False,
           baseline_receipt_SHA=d.sha(N/'reports/development_r6/GENERATION_RECEIPT.json')))
    # Load cloned source functions before denying unrelated filesystem access.
    six=six_candidate_index()
    from budget_ablation_r7 import experimental_serializer
    experimental_serializer()
    from landlock import sandbox
    rows = rows[shard::4]
    baseline_files = [BASE/f"{row['uid']}.json" for row in rows]
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,d.B/'.venv',d.B/'Qwen3.5-9B',
             N/'src',N/'core',N/'validation',d.OLD/'captures',d.OLD/'retrieved',
             d.V11/'ISSUE_ONLY_INPUTS.json',*baseline_files,'/proc/self','/dev/null'],[V,O])
    denied=0
    for p in [d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json',
              d.R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json',BASE/'PRIVATE_SCORED_ROWS.json']:
        try: p.read_bytes(); raise AssertionError('label readable')
        except PermissionError: denied+=1
    receipt=[]; started=time.monotonic()
    for i,row in enumerate(rows):
        uid=row['uid']; prior=BASE/f'{uid}.json'; assert d.sha(prior)==basehash[uid]
        old=d.read(prior); cap=d.OLD/'captures'/f'{uid}.json.gz'; assert d.sha(cap)==old['capture_SHA']
        s=json.load(gzip.open(cap,'rt'))['snapshot']; c3=old['selected']
        ret=d.read(d.OLD/'retrieved'/f'{uid}.json')
        assert hashlib.sha256(row['issue'].encode()).hexdigest()==ret['issue_SHA']
        c6=six(s,row['issue'],task_uid=uid,session_id='r7-budget-dev')['focus']
        assert [e['entity_id'] for e in c6[:3]]==[e['entity_id'] for e in c3], 'candidate prefix drift'
        out={}; elapsed={}
        for k,b in ARMS:
            t=time.monotonic(); z=serialize(c3 if k==3 else c6,s,row['issue'],tok,budget=b)
            elapsed[name(k,b)]=time.monotonic()-t
            assert len(z['pi_ids'])<=b and z['pi_ids']==tok.encode(z['pi_text'],add_special_tokens=False)
            assert tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text'] and len(z['windows'])<=3
            for w in z['windows']: assert w['code']==''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
            out[name(k,b)]=z
        assert out['k3_b192']==old['serialized']['novelty_cost_expand'], 'frozen R6 output drift'
        p=V/f'{uid}.json'; d.save(p,dict(uid=uid,selected={'3':c3,'6':c6},serialized=out,elapsed=elapsed))
        receipt.append(dict(uid=uid,SHA=d.sha(p)))
        if (i+1)%10==0: print(json.dumps(dict(generated=i+1,seconds=time.monotonic()-started)),flush=True)
    d.save(O/f'GENERATION_RECEIPT_{shard}.json',dict(UTC=d.utc(),shard=shard,rows=receipt,count=len(rows),source_SHA=sources,
           actual_Landlock=True,label_denied=denied,baseline_exact=len(rows),candidate_prefix_exact=len(rows),
           wall_seconds=time.monotonic()-started,GPU_jobs=0))


def combine():
    parts=[d.read(O/f'GENERATION_RECEIPT_{i}.json') for i in range(4)]
    rows=sorted([r for part in parts for r in part['rows']],key=lambda r:r['uid'])
    assert len(rows)==len({r['uid'] for r in rows})==607
    assert all(p['source_SHA']==inputs_sha() and p['actual_Landlock'] and p['label_denied']==3 for p in parts)
    assert sum(p['baseline_exact'] for p in parts)==sum(p['candidate_prefix_exact'] for p in parts)==607
    d.save(O/'GENERATION_RECEIPT.json',dict(UTC=d.utc(),rows=rows,count=607,source_SHA=inputs_sha(),
           actual_Landlock=True,label_denied=3,baseline_exact=607,candidate_prefix_exact=607,
           shard_wall_seconds=[p['wall_seconds'] for p in parts],GPU_jobs=0))


def score():
    ref=d.read(O/'GENERATION_RECEIPT.json'); assert ref['count']==607 and ref['source_SHA']==inputs_sha()
    sys.path.insert(0,str(d.R/'ops/icps_bug_coverage_20261023'))
    from coordinates import measure
    from evaluate import metrics,paired,quant
    prior={x['uid']:x for x in d.read(d.O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    audit={x['uid']:x for x in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    locations={hashlib.sha256(('icps-coverage:'+x['instance_id']).encode()).hexdigest():x
               for x in d.read(d.R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json')['rows']}
    scored=[]; costs=collections.defaultdict(list)
    for item in ref['rows']:
        uid=item['uid'];p=V/f'{uid}.json';assert d.sha(p)==item['SHA'];v=d.read(p);a=audit[uid];old=prior[uid]
        h=a['label_hunks'] if old['grade']=='exact_hunk' and old['hunk_map_status']=='mapped' else []
        truth={x['path'] for x in locations[uid]['files']}; row=dict(uid=uid,grade=old['grade'],family=old['family'],metrics={})
        for k,b in ARMS:
            mode=name(k,b);z=v['serialized'][mode]
            row['metrics'][mode]={str(b):measure(v['selected'][str(k)],z['source_map'],truth,h,a['function_targets'])}
            for key,value in [('tokens',len(z['pi_ids'])),('metadata_tokens',z['metadata_tokens_standalone']),
                              ('source_lines',z['source_lines']),('seconds',v['elapsed'][mode])]: costs[mode+'_'+key].append(value)
        scored.append(row)
    result={name(k,b):metrics(scored,name(k,b),b) for k,b in ARMS}
    assert result['k3_b192']['changed_visible_intersect_any']['hits']==171
    comparisons={}
    for k,b in ARMS:
        mode=name(k,b)
        rr=[dict(r,metrics={'R0':{'192':r['metrics']['k3_b192']['192']},
                           'R1':{'192':r['metrics'][mode][str(b)]}}) for r in scored]
        comparisons[mode]={m:paired(rr,192,m) for m in ['changed_visible_intersect_any','changed_visible_full_any']}
    totals={key:{'sum':sum(v),'mean':sum(v)/len(v),'quantiles':quant(v)} for key,v in costs.items()}
    d.save(V/'PRIVATE_SCORED_ROWS.json',scored)
    d.save(O/'AGGREGATE.json',dict(UTC=d.utc(),status='DEVELOPMENT_FACTORIAL_COMPLETE_NOT_ADMITTED',
           arms=ARMS,all607_previously_seen=True,results=result,paired_vs_k3_b192=comparisons,costs=totals,
           baseline_exact=607,candidate_prefix_exact=607,label_denied=ref['label_denied'],actual_Landlock=True,
           source_SHA=ref['source_SHA'],generation_receipt_SHA=d.sha(O/'GENERATION_RECEIPT.json'),
           limitations=['W0 only, not dynamic updates or episode exhaustion.','Development comparisons, not independent confirmation.',
                       'Candidate pool6 retains lexical ranking and max3 windows.','No runtime or model update; R6 frozen.']))
    print(json.dumps({m:{'hit':v['changed_visible_intersect_any']['hits'],'full':v['changed_visible_full_any']['hits'],
          'candidate':v['changed_selected_intersect_any']['hits']} for m,v in result.items()},indent=2),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='generate': generate(int(sys.argv[2]))
    else: {'combine':combine,'score':score}[sys.argv[1]]()
