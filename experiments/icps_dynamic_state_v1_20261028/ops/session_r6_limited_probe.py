"""One first capacity-qualified development W0, no labels or tuning."""
import gzip, hashlib, json, os, pathlib, sys
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1]
R=B/'experiments/pi_repair_state_v2_20261015'
sys.path[:0]=[str(N/'src'),str(N/'core')]
from dynamic_session_r6_r2 import R6DynamicSessionR2
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
rows=sorted(json.loads((R/'.private_icps_v11_window_20261023/ISSUE_ONLY_INPUTS.json').read_text()),key=lambda r:r['uid'])
eligible=0
for row in rows:
    s=json.load(gzip.open(R/'.private_icps_bug_coverage_20261023/captures'/f'{row["uid"]}.json.gz','rt'))['snapshot']
    if len(s['files'])>=1500 or sum(len(v.encode()) for v in s['files'].values())>8388000:continue
    eligible+=1
    assert eligible<=24, 'No limited snapshot among the24'
    if s.get('limited'):break
a=R6DynamicSessionR2(row['issue'],tok,'probe','probe')
def call(x,i):return a.capture(x,task_uid='probe',session_id='probe',logical_call_id=str(i),seq=i)
call(s,0);p='pi_density_probe_current.py'
new=dict(s,files=dict(s['files'],**{p:'def observed_change(x):\n    return x + 123\n'}))
call(new,1);call(new,1);call(new,2)
call(dict(new,files=dict(new['files'],**{p:'def observed_change(x):\n    return x - 987\n'})),3)
call(new,4);z=call(s,5)
out=dict(capacity_qualified_position=eligible,snapshot_limited=s.get('limited',False),has_unobserved='unobserved' in z['pi_text'],has_missing='missing' in z['pi_text'],has_unknown='unknown' in z['pi_text'],unknown=z['unknown'],tokens=len(z['pi_ids']),original_assertion_pass=('missing' in z['pi_text'] or 'unknown' in z['pi_text']),expected_incomplete_capture_status='unobserved',actual_source_SHA=hashlib.sha256((N/'src/dynamic_session_r6_r2.py').read_bytes()).hexdigest(),labels_read=False,GPU_jobs=0)
with (N/'reports/R6_SESSION_LIMITED_DELETION_PROBE.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
