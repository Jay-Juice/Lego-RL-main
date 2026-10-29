"""Predeclared R7 window hypotheses: label-isolated construction and separate scoring."""
import collections,gzip,hashlib,json,os,sys,time
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
from budget_ablation_r7 import experimental_serializer
from window_research_r7 import serialize as candidate_serialize
ARMS={'base3':3,'base6':6,'rank6':6,'diverse6':6,'atomic3':3,'atomic_rank6':6,'compact3':3}
V=N/'.private_window_research_r7'; O=N/'reports/window_research_r7'
BASE=N/'.private_budget_ablation_r7_r2'
EXPECTED_RECEIPT='292922522fcad3cd55a60d7801c72886350523f0f11e8ac1ec304193c7613651'
def sources():
    files=['src/window_research_r7.py','src/budget_ablation_r7.py','validation/window_research_r7.py',
           'validation/development.py','validation/landlock.py','R7_WINDOW_RESEARCH_PLAN.md']
    files+=list(d.read(N/'CANDIDATE_FREEZE_R6_SESSION.json')['source_SHA'])
    return {f:d.sha(N/f) for f in files}
def generate(shard):
    os.umask(0o077);assert shard in range(4) and V.is_dir() and O.is_dir()
    rp=N/'reports/budget_ablation_r7_r2/GENERATION_RECEIPT.json';assert d.sha(rp)==EXPECTED_RECEIPT
    reference=d.read(rp); hashes={r['uid']:r['SHA'] for r in reference['rows']}
    rows=sorted(d.read(d.V11/'ISSUE_ONLY_INPUTS.json'),key=lambda r:r['uid']);assert len(rows)==len(hashes)==607
    assert d.sha(d.V11/'ISSUE_ONLY_INPUTS.json')=='98097627c24b76148c5d42fe9b785d5d02285840334f2bb905faf5c2c6e12da6'
    oldhash={r['uid']:r['SHA'] for r in d.read(N/'reports/development_r6/GENERATION_RECEIPT.json')['rows']}
    source=sources()
    for f,h in d.read(N/'CANDIDATE_FREEZE_R6_SESSION.json')['source_SHA'].items():assert d.sha(N/f)==h
    if shard==0:d.save(O/'FROZEN.json',dict(UTC=d.utc(),arms=ARMS,budget=256,source_SHA=source,input_SHA=d.sha(d.V11/'ISSUE_ONLY_INPUTS.json'),baseline_receipt_SHA=EXPECTED_RECEIPT,confirmation_used=False))
    tok=d.tokenizer(); baseline=experimental_serializer();rows=rows[shard::4]
    from landlock import sandbox
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,d.B/'.venv',d.B/'Qwen3.5-9B',N/'src',N/'core',N/'validation',
             d.OLD/'captures',d.V11/'ISSUE_ONLY_INPUTS.json',*[BASE/f"{r['uid']}.json" for r in rows],*[N/'.private_development_r6'/f"{r['uid']}.json" for r in rows],'/proc/self','/dev/null'],[V,O])
    denied=0
    for p in [d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json',d.R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json',
              N/'.private_development_r6/PRIVATE_SCORED_ROWS.json',BASE/'PRIVATE_SCORED_ROWS.json']:
        try:p.read_bytes();raise AssertionError('label readable')
        except PermissionError:denied+=1
    receipt=[];started=time.monotonic()
    for i,row in enumerate(rows):
        uid=row['uid'];bp=BASE/f'{uid}.json';assert d.sha(bp)==hashes[uid];old=d.read(bp)
        original=N/'.private_development_r6'/f'{uid}.json';assert d.sha(original)==oldhash[uid]
        cap=d.OLD/'captures'/f'{uid}.json.gz';assert d.sha(cap)==d.read(original)['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot']
        # Prior baseline receipt pins candidate identities, and exact replay pins their source/issue output.
        c=old['selected'];fresh=baseline(c['3'],snapshot,row['issue'],tok,budget=256,variant='novelty_cost_expand')
        assert fresh==old['serialized']['k3_b256'],'baseline drift'
        out={};elapsed={}
        for mode,k in ARMS.items():
            t=time.monotonic()
            z=old['serialized'][f'k{k}_b256'] if mode.startswith('base') else candidate_serialize(c[str(k)],snapshot,row['issue'],tok,budget=256,variant=mode)
            elapsed[mode]=time.monotonic()-t
            assert len(z['pi_ids'])<=256 and z['pi_ids']==tok.encode(z['pi_text'],add_special_tokens=False)
            assert tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text'] and len(z['windows'])<=3
            for j,w in enumerate(z['windows']):
                assert w['code']==''.join(snapshot['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
                assert not any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:j])
            out[mode]=z
        p=V/f'{uid}.json';d.save(p,dict(uid=uid,selected=c,serialized=out,elapsed=elapsed,capture_SHA=d.sha(cap)))
        receipt.append(dict(uid=uid,SHA=d.sha(p)))
        if (i+1)%10==0:print(json.dumps(dict(generated=i+1,seconds=time.monotonic()-started)),flush=True)
    d.save(O/f'GENERATION_RECEIPT_{shard}.json',dict(UTC=d.utc(),shard=shard,rows=receipt,count=len(rows),source_SHA=source,actual_Landlock=True,label_denied=denied,baseline_exact=len(rows),wall_seconds=time.monotonic()-started,GPU_jobs=0))
def combine():
    parts=[d.read(O/f'GENERATION_RECEIPT_{i}.json') for i in range(4)]
    rows=sorted([r for p in parts for r in p['rows']],key=lambda r:r['uid'])
    assert len(rows)==len({r['uid'] for r in rows})==607
    assert all(p['source_SHA']==sources() and p['actual_Landlock'] and p['label_denied']==4 for p in parts)
    assert sum(p['baseline_exact'] for p in parts)==607
    d.save(O/'GENERATION_RECEIPT.json',dict(UTC=d.utc(),rows=rows,count=607,source_SHA=sources(),actual_Landlock=True,label_denied=4,baseline_exact=607,shard_wall_seconds=[p['wall_seconds'] for p in parts],GPU_jobs=0))
def score():
    ref=d.read(O/'GENERATION_RECEIPT.json');assert ref['count']==607 and ref['source_SHA']==sources()
    sys.path.insert(0,str(d.R/'ops/icps_bug_coverage_20261023'))
    from coordinates import measure
    from evaluate import metrics,paired,quant
    prior={r['uid']:r for r in d.read(d.O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    audit={r['uid']:r for r in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    locations={hashlib.sha256(('icps-coverage:'+r['instance_id']).encode()).hexdigest():r for r in d.read(d.R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json')['rows']}
    rows=[];costs=collections.defaultdict(list);density={m:collections.Counter() for m in ARMS}
    for item in ref['rows']:
        uid=item['uid'];p=V/f'{uid}.json';assert d.sha(p)==item['SHA'];v=d.read(p);a=audit[uid];old=prior[uid]
        hunks=a['label_hunks'] if old['grade']=='exact_hunk' and old['hunk_map_status']=='mapped' else []
        truth={x['path'] for x in locations[uid]['files']};row=dict(uid=uid,grade=old['grade'],family=old['family'],metrics={})
        want={(h['file'],i) for h in hunks for i in h['changed_lines']}
        for mode,k in ARMS.items():
            z=v['serialized'][mode];m=measure(v['selected'][str(k)],z['source_map'],truth,hunks,a['function_targets']);row['metrics'][mode]={'256':m}
            for key,val in [('tokens',len(z['pi_ids'])),('metadata_tokens',z['metadata_tokens_standalone']),('source_lines',z['source_lines']),('seconds',v['elapsed'][mode])]:costs[mode+'_'+key].append(val)
            if hunks:
                visible={(e['file'],s['line']) for e in z['source_map'] for s in e['pi_emitted_source_spans_W0'] if s['line_complete']}
                density[mode].update(tasks=1,tokens=len(z['pi_ids']),target_lines_visible=len(want&visible),target_lines=len(want),source_lines=len(visible),task_hits=int(m['changed_visible_intersect_any']),full_hits=int(m['changed_visible_full_any']))
        rows.append(row)
    results={m:metrics(rows,m,256) for m in ARMS};assert results['base3']['changed_visible_intersect_any']['hits']==179 and results['base6']['changed_visible_intersect_any']['hits']==170
    comparisons={}
    for mode in ARMS:
        rr=[dict(r,metrics={'R0':r['metrics']['base3'],'R1':r['metrics'][mode]}) for r in rows]
        comparisons[mode]={k:paired(rr,256,k) for k in ['changed_visible_intersect_any','changed_visible_full_any']}
        q=density[mode];q['target_lines_per1000_PI_tokens']=1000*q['target_lines_visible']/q['tokens'];q['hit_tasks_per1000_PI_tokens']=1000*q['task_hits']/q['tokens'];q['visible_target_line_fraction']=q['target_lines_visible']/q['source_lines']
    d.save(V/'PRIVATE_SCORED_ROWS.json',rows)
    d.save(O/'AGGREGATE.json',dict(UTC=d.utc(),status='DEVELOPMENT_WINDOW_RESEARCH_COMPLETE_NOT_ADMITTED',arms=ARMS,budget=256,all607_previously_seen=True,results=results,paired_vs_base3=comparisons,density_proxies=density,costs={k:dict(mean=sum(v)/len(v),sum=sum(v),quantiles=quant(v)) for k,v in costs.items()},baseline_exact=607,actual_Landlock=True,label_denied=4,source_SHA=ref['source_SHA'],generation_receipt_SHA=d.sha(O/'GENERATION_RECEIPT.json'),limitations=['W0 only; no dynamic or episode integration.','Reused development set, no independent confirmation.','Density proxies measure location evidence, not semantic or RL benefit.','All hypotheses fixed before this run; no per-case tuning.']))
    print(json.dumps({m:dict(hit=r['changed_visible_intersect_any']['hits'],full=r['changed_visible_full_any']['hits'],mean_tokens=sum(costs[m+'_tokens'])/607,density=density[m]) for m,r in results.items()},indent=2),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='generate':generate(int(sys.argv[2]))
    else:{'combine':combine,'score':score}[sys.argv[1]]()
