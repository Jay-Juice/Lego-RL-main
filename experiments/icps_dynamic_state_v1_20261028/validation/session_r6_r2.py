"""Label-denied session composition checks on real W0 and constructed events."""
import collections, gzip, hashlib, json, os, pathlib, sys, time
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1]
R=B/'experiments/pi_repair_state_v2_20261015'
OLD=R/'.private_icps_bug_coverage_20261023';V=N/'.private_development_r6'
O=N/'reports/session_r6_r2'
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
from dynamic_session_r6_r2 import R6DynamicSessionR2 as R6DynamicSession
from dense_state import status_facts
from landlock import sandbox
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def main():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
    inp=R/'.private_icps_v11_window_20261023/ISSUE_ONLY_INPUTS.json'
    inputs=sorted(read(inp),key=lambda r:r['uid']);assert len(inputs)==607
    frozen=read(N/'CANDIDATE_FREEZE_R6.json')
    for p,h in frozen['source_SHA'].items():assert sha(N/p)==h
    receipt=read(N/'reports/development_r6/GENERATION_RECEIPT.json')
    hashes={r['uid']:r['SHA'] for r in receipt['rows']}
    O.mkdir(exist_ok=False)
    paths=[V/f'{r["uid"]}.json' for r in inputs]
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,B/'.venv',B/'Qwen3.5-9B',N/'src',N/'core',N/'validation',OLD/'captures',inp,'/proc/self','/dev/null']+paths,[O])
    denied=0
    for p in [OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json',V/'PRIVATE_SCORED_ROWS.json']:
        try:p.read_bytes();raise AssertionError('labels readable')
        except PermissionError:denied+=1
    counts=collections.Counter();t=time.monotonic();dynamic=[]
    def call(sess,s,i):return sess.capture(s,task_uid=sess.identity[0],session_id=sess.identity[1],logical_call_id=str(i),seq=i)
    for i,row in enumerate(inputs):
        uid=row['uid'];p=V/f'{uid}.json';assert sha(p)==hashes[uid];expected=read(p)
        cap=OLD/'captures'/f'{uid}.json.gz';assert sha(cap)==expected['capture_SHA']
        s=json.load(gzip.open(cap,'rt'))['snapshot']
        sess=R6DynamicSession(row['issue'],tok,uid,uid);z=call(sess,s,0)
        e=expected['serialized']['novelty_cost_expand']
        facts=status_facts(sess.initial,s,{})
        counts['status_path_cases']+=bool(facts)
        counts['candidate_identity_exact']+=[x['entity_id'] for x in sess.initial]==[x['entity_id'] for x in expected['selected']]
        counts['initial_payload_exact']+={k:z[k] for k in e}==e
        counts['cases']+=1
        assert len(z['pi_ids'])<=192 and tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text']
        if len(dynamic)<24:
            if len(s['files'])>=1500 or sum(len(v.encode()) for v in s['files'].values())>8388000:counts['capacity_excluded']+=1
            else:dynamic.append((row,s,sess))
        if (i+1)%50==0:print(json.dumps(dict(initial_checked=i+1,counts=counts,seconds=time.monotonic()-t)),flush=True)
    save(O/'INITIAL_COMPARISON.json',dict(counts=counts,label_paths_denied=denied,actual_Landlock=True,seconds=time.monotonic()-t))
    assert counts['initial_payload_exact']==counts['candidate_identity_exact']==607, 'W0 drift requires audit; do not admit'
    assert len(dynamic)==24
    outcomes=collections.Counter();max_update=0
    for row,s,sess in dynamic:
        path='pi_density_probe_current.py';assert path not in s['files']
        new=dict(s,files=dict(s['files'],**{path:'def observed_change(x):\n    return x + 123\n'}))
        z=call(sess,new,1);left=sess.remaining
        assert any(w['file']==path and w['start']<=2<=w['end'] for w in z['windows']);outcomes['addition']+=1
        assert call(sess,new,1)==z and sess.remaining==left;outcomes['retry']+=1
        assert call(sess,new,2)['pi_ids']==[] and sess.remaining==left;outcomes['noop']+=1
        modified=dict(new,files=dict(new['files'],**{path:'def observed_change(x):\n    return x - 987\n'}))
        b=call(sess,modified,3);a=call(sess,new,4)
        assert b['pi_ids'] and a['pi_ids'] and b['state_hash']!=a['state_hash'];outcomes['edit_rollback']+=1
        deleted=call(sess,s,5);assert 'missing' in deleted['pi_text'] or 'unknown' in deleted['pi_text'];outcomes['deletion']+=1
        for z,snap in [(z,new),(b,modified),(a,new),(deleted,s)]:
            assert len(z['pi_ids'])<=128;max_update=max(max_update,len(z['pi_ids']))
            assert tok.decode(z['pi_ids'],skip_special_tokens=False)==z['pi_text']
            for w in z['windows']:assert w['code']==''.join(snap['files'][w['file']].splitlines(True)[w['start']-1:w['end']])
        for what,func in [('late',lambda:call(sess,s,4)),('retry_change',lambda:call(sess,new,5)),('identity',lambda:sess.capture(s,task_uid='foreign',session_id=sess.identity[1],logical_call_id='6',seq=6))]:
            try:func();raise AssertionError(what+' accepted')
            except ValueError:outcomes[what+'_rejected']+=1
        assert sess.remaining>=0
    boundary=R6DynamicSession('function f returns x',tok,'boundary','boundary')
    a=dict(stable=True,limited=False,files={'a.py':'def f(x):\n    return x+1\n','b.py':'# unchanged\n'})
    b=dict(a,files=dict(a['files'],**{'b.py':'# changed unrelated comment\n'}))
    first=call(boundary,a,0);left=boundary.remaining;unchanged=call(boundary,b,1)
    assert unchanged['pi_ids']==[] and boundary.remaining==left
    outcomes['initial_update_semantic_boundary_nocharge']=1
    # Actual tokenizer natural exhaustion on varying current source, no budget edits.
    small=R6DynamicSession('function f returns x',tok,'small','small');spent=0
    for i in range(200):
        z=call(small,dict(stable=True,limited=False,files={'a.py':f'def f(x):\n    return x + {i}\n'}),i)
        spent+=len(z['pi_ids']);assert spent+small.remaining==4096
        if small.exhausted:break
    assert small.exhausted and 'exhausted' in z['pi_text']
    out=dict(status='SESSION_CONTRACTS_PASS_NOT_ONLINE_ADMISSION',initial=counts,constructed=outcomes,cases=24,max_update_tokens=max_update,natural_exhaustion_calls=i+1,spent=spent,remaining=small.remaining,actual_Landlock=True,label_paths_denied=denied,budgets=[192,128,4096],wall_seconds=time.monotonic()-t,GPU_jobs=0,optimizer_steps=0,limitations=['607 development real W0 equivalence only.','24 subsequent sequences are constructed events, not actual Actor rollout.','Independent confirmation and online/Harbor/GPU admission remain pending.'])
    save(O/'AGGREGATE.json',out);print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
