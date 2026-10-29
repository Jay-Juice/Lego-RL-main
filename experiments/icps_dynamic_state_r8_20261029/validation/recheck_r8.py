"""Frozen R8 existing-cohort recheck. Generator denied labels and prior outputs."""
import collections,datetime,gzip,hashlib,json,os,pathlib,sys,time,subprocess
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1]
P=B/'experiments/icps_dynamic_state_v1_20261028';R=B/'experiments/pi_repair_state_v2_20261015'
V=P/'.private_confirmation_r6';W=N/'.private_recheck_r8';O=N/'reports/recheck_r8'
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sources():
 paths=[p for folder in ('src','core') for p in sorted((N/folder).glob('*.py')) if not p.name.startswith(('formal_','gpu_','launch_','prepare_','resolve_','v11_runtime','full_'))]
 paths += [N/'validation'/name for name in ('recheck_r8.py','landlock.py','instruction_transport.py')]
 return {str(p.relative_to(N)):sha(p) for p in paths}
def worker(k):
 from transformers import AutoTokenizer
 from dynamic_session_r8 import R8DynamicSession
 from instruction_transport import verify
 tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
 manifest=read(V/'MANIFEST.json');receipt=read(V/'CAPTURE_RECEIPT.json')
 assert receipt['manifest_SHA']==sha(V/'MANIFEST.json')
 assert sha(V/'MANIFEST.json')=='3b55b245ca7b2cf41732b443094e85943c8fca1d95183555fbed844c3116c730'
 refs={r['uid']:r for r in receipt['rows']}
 transport=read(V/'INSTRUCTION_TRANSPORT.json');witness={r['uid']:r for r in transport['rows']}
 frozen=read(O/'FROZEN.json');assert frozen['source']==sources()
 from landlock import sandbox
 sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,B/'.venv',B/'Qwen3.5-9B',N/'src',N/'core',N/'validation',V/'captures','/proc/self','/dev/null'],[W/'generated',W/'receipts'])
 denied=0
 for p in [R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json',R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json',V/'generated_transport_r3']:
  try:
   p.read_bytes() if p.suffix else list(p.iterdir())
   raise AssertionError('forbidden input accessible')
  except PermissionError:denied+=1
 rows=[];started=time.monotonic()
 for i,row in enumerate(manifest['rows']):
  if i%4!=k:continue
  uid=row['uid'];ref=refs[uid]
  if ref['status']!='COMPLETE':rows.append(dict(uid=uid,status=ref['status']));continue
  cap=V/'captures'/f'{uid}.json.gz';assert sha(cap)==ref['capture_SHA']
  raw=json.load(gzip.open(cap,'rt'));verify(raw['issue'],row['instruction_SHA'],ref['capture_SHA'],witness[uid])
  session=R8DynamicSession(raw['issue'],tok,uid,'R8_RECHECK')
  z=session.capture(raw['snapshot'],task_uid=uid,session_id='R8_RECHECK',logical_call_id='0',seq=0)
  assert len(z['pi_ids'])<=1024 and z['pi_ids']==tok.encode(z['pi_text'],add_special_tokens=False)
  assert tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text']
  for w in z['windows']:assert w['code']==''.join(raw['snapshot']['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
  dst=W/'generated'/f'{uid}.json'
  save(dst,dict(uid=uid,selected_by_mode={'r8':session.initial},serialized={'r8':z},capture_SHA=ref['capture_SHA']))
  rows.append(dict(uid=uid,status='GENERATED',SHA=sha(dst)))
  if len(rows)%25==0:print(k,len(rows),flush=True)
 save(W/'receipts'/f'{k}.json',dict(rows=rows,denied=denied,wall_seconds=time.monotonic()-started))
def generate():
 os.umask(0o077);W.mkdir();(W/'generated').mkdir();(W/'receipts').mkdir();O.mkdir()
 source=sources();save(O/'FROZEN.json',dict(source=source,manifest_SHA=sha(V/'MANIFEST.json'),capture_receipt_SHA=sha(V/'CAPTURE_RECEIPT.json'),policy='one frozen R8 recheck, no tuning',budget=1024))
 jobs=[subprocess.Popen([sys.executable,'-B',__file__,'worker',str(k)]) for k in range(4)]
 codes=[j.wait() for j in jobs];assert codes==[0]*4,codes
 receipts=[read(W/'receipts'/f'{k}.json') for k in range(4)]
 rows=[r for x in receipts for r in x['rows']];assert len(rows)==2826 and len({r['uid'] for r in rows})==2826
 assert source==sources()
 save(O/'GENERATION_RECEIPT.json',dict(source=source,rows=rows,Landlock_denials=sum(x['denied'] for x in receipts),worker_wall_seconds=[x['wall_seconds'] for x in receipts]))
def score():
    os.umask(0o077);receipt=read(O/'GENERATION_RECEIPT.json');assert receipt['source']==sources()
    frozen=read(O/'FROZEN.json');assert frozen['manifest_SHA']==sha(V/'MANIFEST.json')
    assert frozen['capture_receipt_SHA']==sha(V/'CAPTURE_RECEIPT.json')
    manifest=read(V/'MANIFEST.json');refs={r['uid']:r for r in receipt['rows']}
    assert len(refs)==len(manifest['rows'])
    sys.path.insert(0,str(R/'ops/icps_bug_coverage_20261023'))
    from coordinates import verify_hunks,functions_for,measure,parse_old_side
    from evaluate import metrics,paired,quant
    goldpath=R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json'
    locpath=R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json'
    assert sha(goldpath)=='3cc1a18235ccbf8bb95934fde27983aa03539c3e4dffb7a919b3f85532193b04'
    assert sha(locpath)=='dd958c2372fb0f8e652d2af2452e333ae3e849aa8e5d173eb5b9cdcd0d159471'
    labels={r['instance_id']:r for r in read(goldpath)['rows']};locations={r['instance_id']:r for r in read(locpath)['rows']}
    old_refs={r['uid']:r for r in read(P/'reports/confirmation_r6_transport_r3/GENERATION_RECEIPT.json')['rows']}
    rr=[];mismatch=[];costs=collections.defaultdict(list);density=collections.defaultdict(collections.Counter)
    for row in manifest['rows']:
        uid=row['uid'];ref=refs[uid];label=labels[row['instance_id']];loc=locations[row['instance_id']]
        assert loc['confidence']=='exact_hunk'
        r=dict(uid=uid,family=row['family'],grade='exact_hunk',status=ref['status'],metrics={});rr.append(r)
        if ref['status']!='GENERATED':continue
        p=W/'generated'/f'{uid}.json';assert sha(p)==ref['SHA'];d=read(p)
        oldref=old_refs[uid]; assert oldref['status']=='GENERATED'
        oldpath=V/'generated_transport_r3'/f'{uid}.json'; assert sha(oldpath)==oldref['SHA']
        old=read(oldpath); d['serialized']['r6_session']=old['serialized']['r6_session']
        d['selected_by_mode']['r6_session']=old['selected']
        cap=V/'captures'/f'{uid}.json.gz';assert sha(cap)==d['capture_SHA']
        raw=json.load(gzip.open(cap,'rt'));files=raw['snapshot']['files'];image=raw['image']
        assert raw['head'] is None or raw['head']==label['buggy_head'],'HEAD identity mismatch'
        assert image['Dockerfile_SHA']==label['prepared_assets_sha256']['environment/Dockerfile'],'Dockerfile identity mismatch'
        assert image['base_layer_prefix_verified'] and image['declared_base']==label['base_image_digest'],'base identity mismatch'
        patch=pathlib.Path(label['patch_path']);assert sha(patch)==label['repair_patch_sha256']
        patch_bytes=patch.read_bytes();truth={x['path'] for x in loc['files']}
        assert {x['file'] for x in parse_old_side(patch_bytes)}==truth
        mapping=verify_hunks(patch_bytes,files);r['mapping']=mapping['reason']
        if mapping['reason'] in {'buggy_side_context_anchor_mismatch','buggy_file_blob_identity_mismatch'}:mismatch.append(dict(uid=uid,reason=mapping['reason']))
        hunks=mapping['hunks'];functions,_=functions_for(hunks,files)
        targets={(h['file'],n) for h in hunks for n in h['changed_lines']}
        for mode,z in d['serialized'].items():
            r['metrics'][mode]={'192':measure(d['selected_by_mode'][mode],z['source_map'],truth,hunks,functions)}
            for k in ['pi_raw_tokens','source_lines']:costs[mode+'_'+k].append(z[k])
            if hunks:
                visible={(m['file'],p['line']) for m in z['source_map'] for p in m['pi_emitted_source_spans_W0'] if p['line_complete']}
                density[mode]['target_lines']+=len(targets&visible);density[mode]['actual_tokens']+=len(z['pi_ids'])
    save(W/'SCORED_ROWS.json',rr)
    if mismatch:
        save(O/'SOURCE_MISMATCH_STOP.json',dict(count=len(mismatch),details_private=True))
        raise RuntimeError('source mapping identity mismatch; no coverage admission')
    result={m:metrics(rr,m,192) for m in ['r6_session','r8']}
    paired_rows=[dict(r,metrics={'R0':r['metrics'].get('r6_session',{}),'R1':r['metrics'].get('r8',{})}) for r in rr]
    keys=['changed_visible_intersect_any','changed_visible_full_any','changed_selected_intersect_any']
    comparison={k:paired(paired_rows,192,k) for k in keys}
    primary=comparison['changed_visible_intersect_any'];full=comparison['changed_visible_full_any']
    passed=bool(primary.get('n',0) and primary['delta']>0 and primary['repo_cluster_CI95'][0]>0 and full['delta']>=0)
    out=dict(UTC=utc(),status='EXISTING_CONFIRMATION_RECHECK_PASS' if passed else 'EXISTING_CONFIRMATION_RECHECK_NOT_PASSED',
        coverage_admission=passed,training_admitted=False,nominal_tasks=len(rr),families=len({r['family'] for r in rr}),
        results=result,paired=comparison,costs={k:quant(v) for k,v in costs.items()},density=dict(density),
        capture_status_counts=dict(collections.Counter(r['status'] for r in rr)),mapping_counts=dict(collections.Counter(r.get('mapping','capture_unavailable') for r in rr)),
        source=receipt['source'],manifest_SHA=frozen['manifest_SHA'],generation_receipt_SHA=sha(O/'GENERATION_RECEIPT.json'),
        scorer_sources_SHA={name:sha(R/'ops/icps_bug_coverage_20261023'/name) for name in ['coordinates.py','evaluate.py']},
        limitations=['Existing R6 confirmation cohort reused once for frozen R8; NOT fresh blind confirmation. R6 cap192 vs R8 cap1024 combines budget and design effects; no pure same-budget causal claim.',
        'All unavailable/unmapped tasks remain in nominal denominator and strict hit lower bounds; no replacements.',
        'No selector changes or alternative-variant scores on this confirmation set.',
        'Online integration, Harbor, causality/gather, SAO parity and eight-GPU admission remain required.'])
    save(O/'AGGREGATE.json',out)
    print(json.dumps(dict(status=out['status'],nominal=out['nominal_tasks'],primary=primary,full=full,results=result),indent=2),flush=True)


if __name__=='__main__':
 if sys.argv[1]=='worker':worker(int(sys.argv[2]))
 else:{'generate':generate,'score':score}[sys.argv[1]]()
