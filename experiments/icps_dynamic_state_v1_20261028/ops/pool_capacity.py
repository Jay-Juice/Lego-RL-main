"""Scorer-only capacity audit; no generated PI or selection parameters exported."""
import gzip,json,os,pathlib,sys
N=pathlib.Path(__file__).resolve().parents[1]
B=N.parents[1];R=B/'experiments/pi_repair_state_v2_20261015';OLD=R/'.private_icps_bug_coverage_20261023'
sys.path[:0]=[str(N/'src'),str(N/'core')]
from dense_state import render
from window_serializer import resolve
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from transformers import AutoTokenizer
import numpy as np
tok=AutoTokenizer.from_pretrained(B/'Qwen3.5-9B',local_files_only=True)
caps=json.loads((N/'.private_development_r1/PRIVATE_CAPACITY.json').read_text())
costs=[];lengths=[];single=[]
for c in caps:
    if not c['candidate']:continue
    uid=c['uid'];s=json.load(gzip.open(OLD/'captures'/f'{uid}.json.gz','rt'))['snapshot']
    candidates=json.loads((OLD/'retrieved'/f'{uid}.json').read_text())['selected']['R0']
    ws=[]
    for e in resolve(candidates,s['files']):
        if not e['available']:continue
        code=''.join(s['files'][e['file']].splitlines(True)[e['start_line']-1:e['end_line']])
        ws.append(dict(file=e['file'],start=e['start_line'],end=e['end_line'],code=code,unit='context'))
    costs.append(len(tok.encode(render(ws),add_special_tokens=False)))
    lengths.append(sum(w['end']-w['start']+1 for w in ws))
    single.append(min(len(tok.encode(render([w]),add_special_tokens=False)) for w in ws))
def q(v):return dict(n=len(v),median=float(np.median(v)),p90=float(np.quantile(v,.9)),max=int(max(v)))
out=dict(candidate_hit_tasks=len(costs),full_top3_source_tokens=q(costs),full_top3_lines=q(lengths),
         entire_pool_fits_192=sum(x<=192 for x in costs),smallest_whole_candidate_fits_192=sum(x<=192 for x in single),
         target_one_line_fits_192=242,oracle_used_only_to_define_scored_subset=True,
         note='Full candidate bodies can overlap (class and method); this is literal full-top3 representation cost, not an optimal compression bound. One target line fitting is not a label-blind guarantee of choosing it.')
with (N/'reports/POOL_CAPACITY.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
