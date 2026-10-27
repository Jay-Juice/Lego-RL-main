import copy
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ops'))
from session_receipt_r6 import validate

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.i={'counts':dict(cases=607,candidate_identity_exact=607,initial_payload_exact=607,status_path_cases=0), 'actual_Landlock':True,'label_paths_denied':2}
        self.d=dict(status='DYNAMIC_CONTRACTS_PASS_AWAIT_INITIAL607',cases=24,budgets=[192,128,4096],initial=dict(cases=25,initial_payload_exact=25,candidate_identity_exact=25,capacity_excluded=1),constructed={k:24 for k in ['addition','retry','noop','edit_rollback','deletion','late_rejected','retry_change_rejected','identity_rejected']},max_update_tokens=128,spent=4091,remaining=5,natural_exhaustion_calls=151,actual_Landlock=True,label_paths_denied=2,GPU_jobs=0,optimizer_steps=0)
        self.d['constructed']['initial_update_semantic_boundary_nocharge']=1
        self.f="Traceback (most recent call last):\nvalidation/session_r6_r2.py\ndeleted=call(sess,s,5);assert 'missing' in deleted['pi_text'] or 'unknown' in deleted['pi_text']\nAssertionError\n"
    def test_composed_scopes(self):validate(self.i,self.d,1,0,self.f)
    def test_incomplete_or_mismatched_initial_rejected(self):
        for key in ['cases','candidate_identity_exact','initial_payload_exact']:
            i=copy.deepcopy(self.i);i['counts'][key]=606
            with self.assertRaises(AssertionError):validate(i,self.d,1,0,self.f)
    def test_other_failure_or_pending_rejected(self):
        for original,corrected,f in [(0,0,self.f),(1,1,self.f),(1,0,self.f+'RuntimeError'),(1,0,'AssertionError')]:
            with self.assertRaises(AssertionError):validate(self.i,self.d,original,corrected,f)
    def test_dynamic_budget_and_boundary_failures_rejected(self):
        for k,v in [('spent',4092),('max_update_tokens',129),('cases',23),('actual_Landlock',False)]:
            d=copy.deepcopy(self.d);d[k]=v
            with self.assertRaises(AssertionError):validate(self.i,d,1,0,self.f)
        d=copy.deepcopy(self.d);d['constructed']['initial_update_semantic_boundary_nocharge']=0
        with self.assertRaises(AssertionError):validate(self.i,d,1,0,self.f)
