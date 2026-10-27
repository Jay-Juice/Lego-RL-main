"""Frozen confirmation: label-denied generation, then separate exact scorer."""
import collections
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import sys
import time

N=pathlib.Path(__file__).resolve().parents[1]
B=N.parents[1];R=B/'experiments/pi_repair_state_v2_20261015'
V=N/'.private_confirmation_r6';O=N/'reports/confirmation_r6_transport_r2'
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sources():
    f=read(N/'CANDIDATE_FREEZE_R6_SESSION.json')
    for name,h in f['source_SHA'].items():assert sha(N/name)==h,name
    return dict(generator=f['source_SHA'],candidate_freeze=sha(N/'CANDIDATE_FREEZE_R6_SESSION.json'),
                confirmation=sha(pathlib.Path(__file__)),landlock=sha(N/'validation/landlock.py'),instruction_transport=sha(N/'validation/instruction_transport.py'))

def generate():
    os.umask(0o077);started=time.monotonic();source=sources()
    manifest=read(V/'MANIFEST.json');receipt=read(V/'CAPTURE_RECEIPT.json')
    assert receipt['manifest_SHA']==sha(V/'MANIFEST.json')
    assert manifest['candidate_freeze_SHA']==source['candidate_freeze']
    status={r['uid']:r for r in receipt['rows']};assert set(status)=={r['uid'] for r in manifest['rows']}
    from instruction_transport import verify as verify_instruction
    audit=read(N/'reports/R6_INSTRUCTION_TRANSPORT_AUDIT.json')
    assert sha(V/'INSTRUCTION_TRANSPORT.json')==audit['transport_receipt_SHA']=='78fefa495c070fcc848a4573831e36ebab1ff852c943385feef4f67176d8f332'
    transport=read(V/'INSTRUCTION_TRANSPORT.json')
    assert transport['manifest_SHA']==sha(V/'MANIFEST.json')
    assert transport['capture_receipt_SHA']==sha(V/'CAPTURE_RECEIPT.json')
    witnesses={r['uid']:r for r in transport['rows']}
    assert set(witnesses)=={u for u,r in status.items() if r['status']=='COMPLETE'}
    from transformers import AutoTokenizer
    from issue_program_state import build_initial_index
    from dynamic_session_r6_r2 import R6DynamicSessionR2 as R6DynamicSession
    from window_serializer import serialize as original
    tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
    output=V/'generated_transport_r2';output.mkdir(exist_ok=False);O.mkdir(exist_ok=False)
    save(O/'FROZEN.json',dict(UTC=utc(),source=source,manifest_SHA=sha(V/'MANIFEST.json'),capture_receipt_SHA=sha(V/'CAPTURE_RECEIPT.json'),variants=['S1','r6_session'],budget=192))
    from landlock import sandbox
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,B/'.venv',B/'Qwen3.5-9B',N/'src',N/'core',N/'validation',V/'captures',V/'generated','/proc/self','/dev/null'],[output,O])
    denied=[]
    for p in [R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json',R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json']:
        try:p.read_bytes();raise AssertionError('labels accessible')
        except PermissionError:denied.append(str(p))
    rows=[];prefix_exact=0
    for i,row in enumerate(manifest['rows']):
        ref=status[row['uid']];uid=row['uid']
        if ref['status']!='COMPLETE':
            rows.append(dict(uid=uid,status=ref['status']));continue
        p=V/'captures'/f'{uid}.json.gz';assert sha(p)==ref['capture_SHA']
        raw=json.load(gzip.open(p,'rt'));s=raw['snapshot'];issue=raw['issue']
        assert raw['issue_SHA']==row['instruction_SHA']
        verify_instruction(issue,row['instruction_SHA'],ref['capture_SHA'],witnesses[uid])
        index=build_initial_index(s,issue,task_uid=uid,session_id='CONFIRM_W0')
        candidates=[{k:v for k,v in e.items() if k in {'file','qualified','entity_id','kind','start_line','end_line','syntax','selection','tier','retrieval_score'}} for e in index['focus']]
        session=R6DynamicSession(issue,tok,uid,'CONFIRM_W0')
        current=session.capture(s,task_uid=uid,session_id='CONFIRM_W0',logical_call_id='0',seq=0)
        assert [e['entity_id'] for e in session.initial]==[e['entity_id'] for e in candidates]
        serialized={'S1':original(candidates,s,issue,tok,budget=192),'r6_session':current}
        for z in serialized.values():
            assert len(z['pi_ids'])<=192 and z['pi_ids']==tok.encode(z['pi_text'],add_special_tokens=False)
            assert tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text']
            for w in z['windows']:
                assert w['code']==''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
        payload=dict(uid=uid,selected=candidates,serialized=serialized,capture_SHA=sha(p))
        old=V/'generated'/f'{uid}.json'
        if old.exists():
            assert read(old)==payload,'Previously generated payload drift'
            prefix_exact+=1
        dst=output/f'{uid}.json';save(dst,payload)
        rows.append(dict(uid=uid,status='GENERATED',SHA=sha(dst)))
        if (i+1)%10==0:print(json.dumps(dict(done=i+1,total=len(manifest['rows']))),flush=True)
    save(O/'GENERATION_RECEIPT.json',dict(UTC=utc(),rows=rows,source=source,actual_Landlock=True,label_read_denied=denied,prior_payload_exact=prefix_exact,transport_receipt_SHA=audit['transport_receipt_SHA'],wall_seconds=time.monotonic()-started))
    print('GENERATION_FROZEN',len(rows),flush=True)

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
    rr=[];mismatch=[];costs=collections.defaultdict(list);density=collections.defaultdict(collections.Counter)
    for row in manifest['rows']:
        uid=row['uid'];ref=refs[uid];label=labels[row['instance_id']];loc=locations[row['instance_id']]
        assert loc['confidence']=='exact_hunk'
        r=dict(uid=uid,family=row['family'],grade='exact_hunk',status=ref['status'],metrics={});rr.append(r)
        if ref['status']!='GENERATED':continue
        p=V/'generated_transport_r2'/f'{uid}.json';assert sha(p)==ref['SHA'];d=read(p)
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
            r['metrics'][mode]={'192':measure(d['selected'],z['source_map'],truth,hunks,functions)}
            for k in ['pi_raw_tokens','source_lines','source_tokens_standalone','metadata_tokens_standalone']:costs[mode+'_'+k].append(z[k])
            if hunks:
                visible={(m['file'],p['line']) for m in z['source_map'] for p in m['pi_emitted_source_spans_W0'] if p['line_complete']}
                density[mode]['target_lines']+=len(targets&visible);density[mode]['actual_tokens']+=len(z['pi_ids'])
    save(V/'SCORED_ROWS_transport_r2.json',rr)
    if mismatch:
        save(O/'SOURCE_MISMATCH_STOP.json',dict(count=len(mismatch),details_private=True))
        raise RuntimeError('source mapping identity mismatch; no coverage admission')
    result={m:metrics(rr,m,192) for m in ['S1','r6_session']}
    paired_rows=[dict(r,metrics={'R0':r['metrics'].get('S1',{}),'R1':r['metrics'].get('r6_session',{})}) for r in rr]
    keys=['changed_visible_intersect_any','changed_visible_full_any','changed_selected_intersect_any']
    comparison={k:paired(paired_rows,192,k) for k in keys}
    primary=comparison['changed_visible_intersect_any'];full=comparison['changed_visible_full_any']
    passed=bool(primary.get('n',0) and primary['delta']>0 and primary['repo_cluster_CI95'][0]>0 and full['delta']>=0)
    out=dict(UTC=utc(),status='INDEPENDENT_W0_COVERAGE_PASS' if passed else 'INDEPENDENT_W0_COVERAGE_NOT_PASSED',
        coverage_admission=passed,training_admitted=False,nominal_tasks=len(rr),families=len({r['family'] for r in rr}),
        results=result,paired=comparison,costs={k:quant(v) for k,v in costs.items()},density=dict(density),
        capture_status_counts=dict(collections.Counter(r['status'] for r in rr)),mapping_counts=dict(collections.Counter(r.get('mapping','capture_unavailable') for r in rr)),
        source=receipt['source'],manifest_SHA=frozen['manifest_SHA'],generation_receipt_SHA=sha(O/'GENERATION_RECEIPT.json'),
        scorer_sources_SHA={name:sha(R/'ops/icps_bug_coverage_20261023'/name) for name in ['coordinates.py','evaluate.py']},
        limitations=['Task-level W0 confirmation, principally seen repositories; not repository-held-out. No RL or dynamic rollout claim.',
        'All unavailable/unmapped tasks remain in nominal denominator and strict hit lower bounds; no replacements.',
        'No selector changes or alternative-variant scores on this confirmation set.',
        'Online integration, Harbor, causality/gather, SAO parity and eight-GPU admission remain required.'])
    save(O/'AGGREGATE.json',out)
    print(json.dumps(dict(status=out['status'],nominal=out['nominal_tasks'],primary=primary,full=full,results=result),indent=2),flush=True)

if __name__=='__main__':{'generate':generate,'score':score}[sys.argv[1]]()
