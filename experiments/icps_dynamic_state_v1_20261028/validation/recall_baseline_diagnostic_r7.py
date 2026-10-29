"""Label-free baseline mismatch diagnosis; public output only field names/hashes."""
import gzip,json,sys
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
import recall_windows_r7 as new
import candidate_research_r7 as old
from landlock import sandbox

rows=sorted(d.read(d.V11/'ISSUE_ONLY_INPUTS.json'),key=lambda r:r['uid'])[2::4]
V=N/'.private_recall_windows_r7';BASE=N/'.private_candidate_research_r7'
row=next(r for r in rows if not (V/(r['uid']+'.json')).exists())
bp=BASE/(row['uid']+'.json');cap=d.OLD/'captures'/(row['uid']+'.json.gz')
reference=d.read(bp);assert d.sha(cap)==reference['capture_SHA']
snapshot=json.load(gzip.open(cap,'rt'))['snapshot']
sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,N/'src',N/'core',N/'validation','/proc/self','/dev/null'],[])
a,_=new.build(snapshot,row['issue'],task_uid='diagnostic',session_id='diagnostic')
b,_=old.build(snapshot,row['issue'],task_uid='diagnostic',session_id='diagnostic')
def diff(left,right):
    out=[]
    for i,(x,y) in enumerate(zip(left,right)):
        if x!=y:out.append(dict(position=i,fields=[k for k in sorted(set(x)|set(y)) if x.get(k)!=y.get(k)],same_entity=x['entity_id']==y['entity_id']))
    return dict(lengths=[len(left),len(right)],differences=out)
print(json.dumps(dict(new_vs_saved=diff(a['symbols12'],reference['selected']['symbols12']),
                     old_vs_saved=diff(b['symbols12'],reference['selected']['symbols12']),
                     new_vs_old=diff(a['symbols12'],b['symbols12'])),indent=2))
