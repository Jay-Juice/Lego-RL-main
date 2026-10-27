"""Separate label-denied construction and private-label aggregate scoring.

All 607 examples are development. Capacity oracle is scorer-only, never PI.
"""
import ast,collections,copy,datetime,gzip,hashlib,json,os,pathlib,resource,sys,time
P=pathlib.Path(__file__).resolve().parents[1]
B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
R=B/'experiments/pi_repair_state_v2_20261015'
OLD=R/'.private_icps_bug_coverage_20261023'
V11=R/'.private_icps_v11_window_20261023'
O11=R/'logs/icps_v11_window_20261023'
RUN=sys.argv[2] if len(sys.argv)>2 else 'r1'
assert RUN.isalnum()
V=P/('.private_development_'+RUN);O=P/'reports'/('development_'+RUN)
sys.path[:0]=[str(P/'src'),str(P/'core')]
from dense_state import CONFIG,serialize,render,proposals
from window_serializer import digest
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def tokenizer():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
def sources():return {str(p.relative_to(P)):sha(p) for folder in ['src','core','validation'] for p in (P/folder).rglob('*.py')}

def generate():
    os.umask(0o077);V.mkdir(exist_ok=False);O.mkdir(exist_ok=False)
    tok=tokenizer();inputs=sorted(read(V11/'ISSUE_ONLY_INPUTS.json'),key=lambda x:x['uid']);assert len(inputs)==607
    receipt=read(O11/'GENERATION_RECEIPT.json');basehash={r['uid']:r['output_SHA'] for r in receipt['rows']}
    frozen=dict(UTC=utc(),config=CONFIG,source_SHA=sources(),baseline_receipt_SHA=sha(O11/'GENERATION_RECEIPT.json'),input_SHA=sha(V11/'ISSUE_ONLY_INPUTS.json'),all607_development=True)
    save(O/'FROZEN.json',frozen)
    from landlock import sandbox
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,B/'.venv',B/'Qwen3.5-9B',P/'src',P/'core',P/'validation',OLD/'captures',OLD/'retrieved',V11/'ISSUE_ONLY_INPUTS.json',V11/receipt['output_directory'],'/proc/self','/dev/null'],[V,O])
    denied=[]
    for p in [OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json',R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json']:
        try:p.read_bytes();raise AssertionError('labels readable')
        except PermissionError:denied.append(str(p))
    rows=[];started=time.monotonic()
    for i,r in enumerate(inputs):
        uid=r['uid'];cap=OLD/'captures'/f'{uid}.json.gz';ret=OLD/'retrieved'/f'{uid}.json';base=V11/receipt['output_directory']/f'{uid}.json'
        assert sha(base)==basehash[uid]
        b=read(base);d=read(ret);s=json.load(gzip.open(cap,'rt'))['snapshot'];c=d['selected']['R0']
        assert sha(cap)==b['source_capture_SHA'] and sha(ret)==b['old_retrieval_SHA']
        assert hashlib.sha256(r['issue'].encode()).hexdigest()==d['issue_SHA']
        z={'S1':b['serialized']['S1']['192']};elapsed={}
        for variant in CONFIG['variants']:
            t=time.monotonic();z[variant]=serialize(c,s,r['issue'],tok,variant=variant);elapsed[variant]=time.monotonic()-t
        for k,a in z.items():
            assert len(a['pi_ids'])<=192 and a['pi_ids']==tok.encode(a['pi_text'],add_special_tokens=False)
            assert tok.decode(a['pi_ids'],skip_special_tokens=False)==a['pi_text']
            for w in a['windows']:
                assert w['code']==''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]) and w['code'] in a['pi_text']
        p=V/f'{uid}.json';save(p,dict(uid=uid,selected=c,serialized=z,elapsed=elapsed,capture_SHA=sha(cap)))
        rows.append(dict(uid=uid,SHA=sha(p)))
        if (i+1)%10==0:print(json.dumps(dict(generated=i+1,seconds=time.monotonic()-started)),flush=True)
    save(O/'GENERATION_RECEIPT.json',dict(UTC=utc(),rows=rows,count=len(rows),source_SHA=frozen['source_SHA'],label_read_denied=denied,actual_Landlock=True,wall_seconds=time.monotonic()-started,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,GPU_jobs=0,optimizer_steps=0))
    print('GENERATION_COMPLETE',len(rows),flush=True)

def capacity(c,s,hunks,tok,issue):
    """Diagnostic upper bounds with label access. NEVER used by construction."""
    points=[(h['file'],n) for h in hunks for n in h['changed_lines'] if any(e['file']==h['file'] and e['start_line']<=n<=e['end_line'] for e in c)]
    if not points:return dict(candidate=False)
    windows=[]
    for path,n in points:
        line=s['files'][path].splitlines(True)[n-1]
        windows.append(dict(file=path,start=n,end=n,code=line,unit='line_fragment'))
    linecost=min(len(tok.encode(render([w]),add_special_tokens=False)) for w in windows)
    props=proposals(c,s,issue)
    fitting=[w for w in props if any(w['file']==p and w['start']<=n<=w['end'] for p,n in points)]
    proposalcost=min((len(tok.encode(render([w]),add_special_tokens=False)) for w in fitting),default=None)
    complete=[w for w in fitting if w['unit']=='statement']
    statementcost=min((len(tok.encode(render([w]),add_special_tokens=False)) for w in complete),default=None)
    return dict(candidate=True,minimum_one_line_tokens=linecost,line_fits=linecost<=192,proposal_available=bool(fitting),proposal_fits=proposalcost is not None and proposalcost<=192,statement_fits=statementcost is not None and statementcost<=192)

def score():
    os.umask(0o077);receipt=read(O/'GENERATION_RECEIPT.json');assert receipt['count']==607 and receipt['source_SHA']==sources()
    sys.path.insert(0,str(R/'ops/icps_bug_coverage_20261023'))
    from coordinates import measure
    from evaluate import metrics,paired,quant
    old={x['uid']:x for x in read(O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    audit={x['uid']:x for x in read(OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    loc={hashlib.sha256(('icps-coverage:'+x['instance_id']).encode()).hexdigest():x for x in read(R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json')['rows']}
    inputs={x['uid']:x for x in read(V11/'ISSUE_ONLY_INPUTS.json')}
    rr=[];caps=[];costs=collections.defaultdict(list)
    for ref in receipt['rows']:
        uid=ref['uid'];p=V/f'{uid}.json';assert sha(p)==ref['SHA'];d=read(p);a=audit[uid];prior=old[uid]
        h=a['label_hunks'] if prior['grade']=='exact_hunk' and prior['hunk_map_status']=='mapped' else []
        truth={x['path'] for x in loc[uid]['files']}
        row=dict(uid=uid,grade=prior['grade'],family=prior['family'],metrics={})
        for mode,z in d['serialized'].items():
            m=measure(d['selected'],z['source_map'],truth,h,a['function_targets']);row['metrics'][mode]={'192':m}
            costs[mode+'_tokens'].append(len(z['pi_ids']))
            if mode!='S1':
                costs[mode+'_metadata_tokens'].append(z['metadata_tokens_standalone']);costs[mode+'_source_lines'].append(z['source_lines']);costs[mode+'_seconds'].append(d['elapsed'][mode])
        rr.append(row)
    tok=tokenizer()
    for row in rr:
        uid=row['uid'];a=audit[uid];prior=old[uid]
        if prior['grade']!='exact_hunk' or prior['hunk_map_status']!='mapped':continue
        d=read(V/f'{uid}.json');s=json.load(gzip.open(OLD/'captures'/f'{uid}.json.gz','rt'))['snapshot']
        x=capacity(d['selected'],s,a['label_hunks'],tok,inputs[uid]['issue']);caps.append(dict(uid=uid,**x))
    modes=['S1']+CONFIG['variants'];result={m:metrics(rr,m,192) for m in modes}
    assert result['S1']['changed_visible_intersect_any']['hits']==129 and result['S1']['changed_selected_intersect_any']['hits']==242
    comparison={}
    for mode in CONFIG['variants']:
        pr=[dict(r,metrics={'R0':r['metrics']['S1'],'R1':r['metrics'][mode]}) for r in rr]
        comparison[mode]={k:paired(pr,192,k) for k in ['changed_visible_intersect_any','changed_visible_full_any','pi_visible_function_any','pi_visible_file_any']}
    counts={k:sum(bool(c.get(k)) for c in caps) for k in ['candidate','line_fits','proposal_available','proposal_fits','statement_fits']}
    counts.update(evaluable=len(caps),oracle_only=True,oracle_is_not_deployable=True)
    for mode in modes:counts[mode+'_candidate_conversion']=result[mode]['changed_visible_intersect_any']['hits']/counts['candidate']
    public=dict(UTC=utc(),status='DEVELOPMENT_ONLY_NOT_TRAINING_ADMISSION',all607_previously_seen=True,fixed_budget=[192,128,4096],results=result,paired=comparison,capacity=counts,costs={k:quant(v) for k,v in costs.items()},receipt_SHA=sha(O/'GENERATION_RECEIPT.json'),source_SHA=receipt['source_SHA'],limitations=['Initial W0 coverage does not validate dynamic trajectory coverage.','Capacity oracle uses labels only after all outputs frozen; cannot choose runtime windows.','No independent unseen validation or GPU tests yet.'])
    save(V/'PRIVATE_CAPACITY.json',caps);save(V/'PRIVATE_SCORED_ROWS.json',rr);save(O/'AGGREGATE.json',public)
    print(json.dumps(dict(status=public['status'],hits={m:result[m]['changed_visible_intersect_any']['hits'] for m in modes},capacity=counts,paired=comparison),indent=2),flush=True)

if __name__=='__main__':{'generate':generate,'score':score}[sys.argv[1]]()
