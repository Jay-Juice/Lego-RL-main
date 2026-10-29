"""Synthetic initial-status budget regression; no confirmation labels or scores."""
import json,sys,hashlib
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
from transformers import AutoTokenizer
from dynamic_session_r8 import R8DynamicSession,dispatch
from dynamic_session_r6_r2 import serialize_state as legacy
from dynamic_session_r7_probe import initial,serialize_state as clean_initial

def main():
 tok=AutoTokenizer.from_pretrained(N.parents[1]/'Qwen3.5-9B',local_files_only=True)
 snap={'files':{'sample.py':'def compute_total(x):\n    return x + 1\n'},'stable':True,'limited':False}
 issue='compute_total returns the wrong integer'
 candidates=initial(snap,issue,task_uid='synthetic',session_id='budget')['focus']
 args=dict(delta={},variant='flow_expand',facts=[],status='initial')
 assert dispatch(candidates,snap,issue,tok,budget=1024,**args)==clean_initial(candidates,snap,issue,tok,budget=1024,**args)
 results=[]
 for facts in [[('sample.py','compute_total','parse_unavailable')],[('absent.py','missing','unobserved')]]:
  for limited in [False,True]:
   sample=dict(snap,limited=limited);kw=dict(args,facts=facts)
   actual=dispatch(candidates,sample,issue,tok,budget=1024,**kw)
   expected=legacy(candidates,sample,issue,tok,budget=192,**kw)
   assert actual==expected
   assert len(actual['pi_ids'])<=192 and tok.encode(actual['pi_text'],add_special_tokens=False)==actual['pi_ids']
   assert actual['pi_text']==tok.decode(actual['pi_ids'],skip_special_tokens=False)
   results.append(dict(limited=limited,tokens=len(actual['pi_ids']),legacy_exact=True))
 output=dict(source_SHA=hashlib.sha256((N/'src/dynamic_session_r8.py').read_bytes()).hexdigest(),status='PASS_synthetic_initial_status_fallback',clean_initial_1024_exact=True,fallback_cap=192,update_cap=128,episode_cap=4096,cases=results,confirmation_scores_used=False,GPU=False)
 (N/'reports/INITIAL_STATUS_BUDGET_R8.json').write_text(json.dumps(output,indent=2))
 print(json.dumps(output))
if __name__=='__main__':main()
