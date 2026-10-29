"""Compare the first preserved output with unchanged generator; report types only."""
import gzip,json,pathlib,sys,os,collections
N=pathlib.Path(__file__).resolve().parents[1];B=N.parents[1];V=N/'.private_confirmation_r6'
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from transformers import AutoTokenizer
from issue_program_state import build_initial_index
from dynamic_session_r6_r2 import R6DynamicSessionR2
from window_serializer import serialize
from landlock import sandbox
import hashlib
tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
m=json.loads((V/'MANIFEST.json').read_text());row=next(r for r in m['rows'] if (V/'generated'/f"{r['uid']}.json").exists())
uid=row['uid'];p=V/'captures'/f'{uid}.json.gz';raw=json.load(gzip.open(p,'rt'));old=json.loads((V/'generated'/f'{uid}.json').read_text())
sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,B/'.venv',B/'Qwen3.5-9B',N/'src',N/'core',N/'validation','/proc/self','/dev/null'],[N/'reports'])
index=build_initial_index(raw['snapshot'],raw['issue'],task_uid=uid,session_id='CONFIRM_W0')
candidates=[{k:v for k,v in e.items() if k in {'file','qualified','entity_id','kind','start_line','end_line','syntax','selection','tier','retrieval_score'}} for e in index['focus']]
a=R6DynamicSessionR2(raw['issue'],tok,uid,'CONFIRM_W0')
z=a.capture(raw['snapshot'],task_uid=uid,session_id='CONFIRM_W0',logical_call_id='0',seq=0)
payload=dict(uid=uid,selected=candidates,serialized={'S1':serialize(candidates,raw['snapshot'],raw['issue'],tok,budget=192),'r6_session':z},capture_SHA=old['capture_SHA'])
diff=collections.Counter();paths=[]
def walk(a,b,path='root'):
    if type(a)!=type(b):diff[type(a).__name__+' vs '+type(b).__name__]+=1
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys()&b.keys():walk(a[k],b[k],path+'.'+str(k))
    elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        for i,(x,y) in enumerate(zip(a,b)):walk(x,y,path+'['+str(i)+']')
        if len(a)!=len(b):paths.append(path+'.length')
    elif a!=b:paths.append(path)
walk(old,payload)
out=dict(in_memory_equal=old==payload,json_roundtrip_equal=old==json.loads(json.dumps(payload)),type_mismatch_counts=dict(diff),differing_field_paths=paths[:80],total_differing_leaves=len(paths),labels_read=False,scored_outputs_read=False,selector_changed=False)
with (N/'reports/R6_PREFIX_FIELD_AUDIT.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
