"""Real W0 snapshots with explicitly CONSTRUCTED changes, never real rollout claims."""
import gzip,hashlib,json,os,pathlib,sys,time
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1]
R=B/'experiments/pi_repair_state_v2_20261015'
sys.path[:0]=[str(N/'src'),str(N/'core')]
from dense_state import DynamicSession
from window_serializer import WindowSession
from issue_program_state import build_initial_index
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
inputs=sorted(json.loads((R/'.private_icps_v11_window_20261023/ISSUE_ONLY_INPUTS.json').read_text()),key=lambda r:r['uid'])
variant=sys.argv[1];assert variant in {'body_expand','flow_expand'}

skipped_bounds=0;hits={'old':0,'new':0};noop=0;retry=0;rollback=0;total=0;max_update=0;t=time.monotonic()
for row in inputs:
    s=json.load(gzip.open(R/'.private_icps_bug_coverage_20261023/captures'/f'{row["uid"]}.json.gz','rt'))['snapshot']
    if len(s['files'])>=1500 or sum(len(v.encode()) for v in s['files'].values())>8388000:
        skipped_bounds+=1;continue
    uid=row['uid'];initial=build_initial_index(s,row['issue'],task_uid=uid,session_id=uid)['focus']
    a=WindowSession(initial,row['issue'],tok,uid,uid);b=DynamicSession(row['issue'],tok,uid,uid,variant=variant)
    def call(session,snapshot,i):return session.capture(snapshot,task_uid=uid,session_id=uid,logical_call_id=str(i),seq=i)
    call(a,s,0);call(b,s,0)
    path='pi_density_probe_current.py';assert path not in s['files']
    new=dict(s,files=dict(s['files'],**{path:'def observed_change(x):\n    return x + 123\n'}))
    for name,session in [('old',a),('new',b)]:
        z=call(session,new,1)
        hits[name]+=int(any(w['file']==path and w['start']<=2<=w['end'] for w in z['windows']))
        assert len(z['pi_ids'])<=128
        if name=='new':
            left=session.remaining;assert call(session,new,1)==z and session.remaining==left;retry+=1
            assert call(session,new,2)['pi_ids']==[];noop+=1;max_update=max(max_update,len(z['pi_ids']))
    modified=dict(new,files=dict(new['files'],**{path:'def observed_change(x):\n    return x - 987\n'}))
    z1=call(b,modified,3);z2=call(b,new,4)
    assert z1['pi_ids'] and z2['pi_ids'] and z1['state_hash']!=z2['state_hash'];rollback+=1
    for w in z2['windows']:assert w['code']==''.join(new['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
    total+=1
    if total==24:break
assert total==24
out=dict(variant=variant,cases=total,skipped_source_capacity=skipped_bounds,selection="first24 UID-sorted snapshots with room for added test file; no outcome/labels read",changed_line_visible=hits,unchanged_noop_pass=noop,retry_exact_once_pass=retry,rollback_pass=rollback,max_update_tokens=max_update,budget=[192,128,4096],wall_seconds=time.monotonic()-t,source_SHA=hashlib.sha256((N/'src/dense_state.py').read_bytes()).hexdigest(),evidence='24 real W0 snapshots plus synthetic new-file/change/rollback events. No actual Actor trajectory or real bug-coverage improvement is claimed.',GPU_jobs=0,optimizer_steps=0)
with (N/'reports'/('DYNAMIC_CONSTRUCTED_R4_'+variant+'.json')).open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
