"""Predeclared R7 joint window/budget hypotheses: label-isolated construction and separate scoring."""
import collections,gzip,hashlib,json,os,sys,time
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
from joint_windows_r7 import budget_control
from behavior_windows_r7 import serialize, signals
ARMS={'base256':('passage24',256),'base384':('passage24',384),
      'rank256':('passage24',256),'rank384':('passage24',384),
      'extend256':('passage24',256),'extend384':('passage24',384)}
CONTROLS={m:('base384' if cap==384 else 'base256') for m,(_,cap) in ARMS.items() if not m.startswith('base')}
V=N/'.private_behavior_windows_r7';O=N/'reports/behavior_windows_r7';BASE=N/'.private_recall_windows_r7_r2'
EXPECTED_RECEIPT='c6c2227d8549fa391b9b454e534545b7722123b3296083f82e33c20dccaec366'

def sources():
    files=['src/behavior_windows_r7.py','src/joint_windows_r7.py','src/window_research_r7.py','src/budget_ablation_r7.py',
           'validation/behavior_windows_r7.py','validation/behavior_windows_r7_contracts.py','validation/development.py','validation/landlock.py','R7_BEHAVIOR_WINDOWS_PLAN.md']
    files+=list(d.read(N/'CANDIDATE_FREEZE_R6_SESSION.json')['source_SHA'])
    return {f:d.sha(N/f) for f in files}
def generate(shard):
    os.umask(0o077);assert shard in range(4) and V.is_dir() and O.is_dir()
    rp=N/'reports/recall_windows_r7_r2/GENERATION_RECEIPT.json';assert d.sha(rp)==EXPECTED_RECEIPT
    reference=d.read(rp); hashes={r['uid']:r['SHA'] for r in reference['rows']}
    rows=sorted(d.read(d.V11/'ISSUE_ONLY_INPUTS.json'),key=lambda r:r['uid']);assert len(rows)==len(hashes)==607
    assert d.sha(d.V11/'ISSUE_ONLY_INPUTS.json')=='98097627c24b76148c5d42fe9b785d5d02285840334f2bb905faf5c2c6e12da6'
    source=sources()
    for f,h in d.read(N/'CANDIDATE_FREEZE_R6_SESSION.json')['source_SHA'].items():assert d.sha(N/f)==h
    if shard==0:d.save(O/'FROZEN.json',dict(UTC=d.utc(),arms=ARMS,matching_controls=CONTROLS,source_SHA=source,input_SHA=d.sha(d.V11/'ISSUE_ONLY_INPUTS.json'),baseline_receipt_SHA=EXPECTED_RECEIPT,confirmation_used=False))
    tok=d.tokenizer();rows=rows[shard::4]
    from landlock import sandbox
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,d.B/'.venv',d.B/'Qwen3.5-9B',N/'src',N/'core',N/'validation',
             d.OLD/'captures',d.V11/'ISSUE_ONLY_INPUTS.json',*[BASE/f"{r['uid']}.json" for r in rows],'/proc/self','/dev/null'],[V,O])
    denied=0
    for p in [d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json',d.R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json',
              N/'.private_development_r6/PRIVATE_SCORED_ROWS.json',BASE/'PRIVATE_SCORED_ROWS.json',N/'.private_window_research_r7/PRIVATE_SCORED_ROWS.json',N/'.private_budget_ablation_r7_r2/PRIVATE_SCORED_ROWS.json',N/'.private_joint_windows_r7/PRIVATE_SCORED_ROWS.json',N/'.private_lookahead_windows_r7/PRIVATE_SCORED_ROWS.json',N/'.private_relevance_windows_r7/PRIVATE_SCORED_ROWS.json']:
        try:p.read_bytes();raise AssertionError('label readable')
        except PermissionError:denied+=1
    receipt=[];started=time.monotonic()
    for i,row in enumerate(rows):
        uid=row['uid'];bp=BASE/f'{uid}.json';assert d.sha(bp)==hashes[uid];old=d.read(bp)
        cap=d.OLD/'captures'/f'{uid}.json.gz';assert d.sha(cap)==old['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot']
        c={'passage24':old['selected']['passage24']}
        _,cues,details=signals(c['passage24'],snapshot,row['issue'])
        mechanism=dict(any_prior=any(v and v['prior']>0 for v in cues.values()),any_line_cue=any(v and v['lines'] for v in cues.values()))
        for name in sorted({k for v in details.values() for k in v}):mechanism[name]=sum(v.get(name,0) for v in details.values())
        out={};elapsed={}
        for mode,(key,cap_tokens) in ARMS.items():
            t=time.monotonic()
            if mode.startswith('base'):
                z=budget_control()(c[key],snapshot,row['issue'],tok,budget=cap_tokens,variant='diverse6')
            else:
                z=serialize(c[key],snapshot,row['issue'],tok,budget=cap_tokens,variant='extend' if mode.startswith('extend') else 'rank')
            if mode=='base256':assert z==old['serialized']['passage24_256'],'prior baseline drift'
            elapsed[mode]=time.monotonic()-t
            assert len(z['pi_ids'])<=cap_tokens and z['pi_ids']==tok.encode(z['pi_text'],add_special_tokens=False)
            assert tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text'] and len(z['windows'])<=3
            for j,w in enumerate(z['windows']):
                assert w['code']==''.join(snapshot['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
                assert not any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:j])
            out[mode]=z
        p=V/f'{uid}.json';d.save(p,dict(uid=uid,selected=c,serialized=out,elapsed=elapsed,mechanism=mechanism,capture_SHA=d.sha(cap)))
        receipt.append(dict(uid=uid,SHA=d.sha(p)))
        if (i+1)%10==0:print(json.dumps(dict(generated=i+1,seconds=time.monotonic()-started)),flush=True)
    d.save(O/f'GENERATION_RECEIPT_{shard}.json',dict(UTC=d.utc(),shard=shard,rows=receipt,count=len(rows),source_SHA=source,actual_Landlock=True,label_denied=denied,baseline_exact=len(rows),wall_seconds=time.monotonic()-started,GPU_jobs=0))
def combine():
    parts=[d.read(O/f'GENERATION_RECEIPT_{i}.json') for i in range(4)]
    rows=sorted([r for p in parts for r in p['rows']],key=lambda r:r['uid'])
    assert len(rows)==len({r['uid'] for r in rows})==607
    assert all(p['source_SHA']==sources() and p['actual_Landlock'] and p['label_denied']==9 for p in parts)
    assert sum(p['baseline_exact'] for p in parts)==607
    d.save(O/'GENERATION_RECEIPT.json',dict(UTC=d.utc(),rows=rows,count=607,source_SHA=sources(),actual_Landlock=True,label_denied=9,baseline_exact=607,shard_wall_seconds=[p['wall_seconds'] for p in parts],GPU_jobs=0))
def score():
    ref=d.read(O/'GENERATION_RECEIPT.json');assert ref['count']==607 and ref['source_SHA']==sources()
    sys.path.insert(0,str(d.R/'ops/icps_bug_coverage_20261023'))
    from coordinates import measure
    from evaluate import metrics,paired,quant
    prior={r['uid']:r for r in d.read(d.O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    audit={r['uid']:r for r in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    locations={hashlib.sha256(('icps-coverage:'+r['instance_id']).encode()).hexdigest():r for r in d.read(d.R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json')['rows']}
    rows=[];costs=collections.defaultdict(list);density={m:collections.Counter() for m in ARMS};diagnostic=collections.Counter()
    for item in ref['rows']:
        uid=item['uid'];p=V/f'{uid}.json';assert d.sha(p)==item['SHA'];v=d.read(p);a=audit[uid];old=prior[uid]
        hunks=a['label_hunks'] if old['grade']=='exact_hunk' and old['hunk_map_status']=='mapped' else []
        truth={x['path'] for x in locations[uid]['files']};row=dict(uid=uid,grade=old['grade'],family=old['family'],metrics={})
        want={(h['file'],i) for h in hunks for i in h['changed_lines']}
        for mode,(key,cap_tokens) in ARMS.items():
            z=v['serialized'][mode];m=measure(v['selected'][key],z['source_map'],truth,hunks,a['function_targets']);row['metrics'][mode]={str(cap_tokens):m}
            for key,val in [('tokens',len(z['pi_ids'])),('metadata_tokens',z['metadata_tokens_standalone']),('source_lines',z['source_lines']),('seconds',v['elapsed'][mode])]:costs[mode+'_'+key].append(val)
            if hunks:
                visible={(e['file'],s['line']) for e in z['source_map'] for s in e['pi_emitted_source_spans_W0'] if s['line_complete']}
                density[mode].update(tasks=1,tokens=len(z['pi_ids']),target_lines_visible=len(want&visible),target_lines=len(want),source_lines=len(visible),task_hits=int(m['changed_visible_intersect_any']),full_hits=int(m['changed_visible_full_any']))
        diagnostic.update({k:int(bool(val)) for k,val in v['mechanism'].items()})
        rows.append(row)
    results={m:metrics(rows,m,ARMS[m][1]) for m in ARMS}
    assert results['base256']['changed_selected_intersect_any']['hits']==343
    assert results['base256']['changed_visible_intersect_any']['hits']==205
    def compare(left,right):
        rr=[dict(r,metrics={'R0':{'0':r['metrics'][left][str(ARMS[left][1])]},'R1':{'0':r['metrics'][right][str(ARMS[right][1])]}}) for r in rows]
        return {k:paired(rr,0,k) for k in ['changed_selected_intersect_any','changed_visible_intersect_any','changed_visible_full_any','changed_visible_full_all']}
    comparisons={m:compare(CONTROLS.get(m,'base256'),m) for m in ARMS}
    versus_base12={m:compare('base256',m) for m in ARMS}
    for mode in ARMS:
        q=density[mode];q['target_lines_per1000_PI_tokens']=1000*q['target_lines_visible']/q['tokens'];q['hit_tasks_per1000_PI_tokens']=1000*q['task_hits']/q['tokens'];q['visible_target_line_fraction']=q['target_lines_visible']/q['source_lines']
    d.save(V/'PRIVATE_SCORED_ROWS.json',rows)
    d.save(O/'AGGREGATE.json',dict(UTC=d.utc(),status='DEVELOPMENT_BEHAVIOR_WINDOWS_COMPLETE_NOT_ADMITTED',arms=ARMS,matching_controls=CONTROLS,
        all607_previously_seen=True,results=results,paired_vs_matching_control=comparisons,paired_vs_base256=versus_base12,
        density_proxies=density,source_only_mechanism_task_counts=dict(diagnostic),costs={k:dict(mean=sum(v)/len(v),sum=sum(v),quantiles=quant(v)) for k,v in costs.items()},
        baseline_exact=607,actual_Landlock=True,label_denied=9,source_SHA=ref['source_SHA'],generation_receipt_SHA=d.sha(O/'GENERATION_RECEIPT.json'),
        limitations=['W0 only; no runtime/dynamic/episode integration.','Reused development, unadjusted exploratory comparisons, no independent confirmation.',
            'Density measures target location evidence, not semantic or RL benefit.','Fixed passage24; explicit issue identifiers and approximate scoped AST relations; no semantic model or learned ranking.',
            'Adaptive development after prior aggregate results; no per-case tuning or independent confirmation.']))
    print(json.dumps({m:dict(candidate=r['changed_selected_intersect_any']['hits'],hit=r['changed_visible_intersect_any']['hits'],full=r['changed_visible_full_any']['hits'],mean_tokens=sum(costs[m+'_tokens'])/607,density=density[m]) for m,r in results.items()},indent=2),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='generate':generate(int(sys.argv[2]))
    else:{'combine':combine,'score':score}[sys.argv[1]]()
