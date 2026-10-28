import copy
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import relevance_windows_r7 as r
import candidate_research_r7 as candidates
import candidate_research_r7_contracts as fixtures
from joint_windows_r7 import budget_control

class Contracts(unittest.TestCase):
    def setup_case(self):
        s=fixtures.Contracts().fixture();issue='normalize render strip transform'
        pool=candidates.build(s,issue,task_uid='s',session_id='t')[0]['symbols12']
        return s,issue,pool
    def test_exact_source_caps_determinism_no_mutation(self):
        s,q,p=self.setup_case();saved=copy.deepcopy((s,p))
        for cap in (256,384):
            for arm in ('fused','anchored'):
                z=r.serialize(p,s,q,fixtures.Bytes(),budget=cap,variant=arm)
                self.assertEqual(z,r.serialize(p,s,q,fixtures.Bytes(),budget=cap,variant=arm))
                self.assertLessEqual(len(z['pi_ids']),cap);self.assertLessEqual(len(z['windows']),3)
                self.assertEqual(fixtures.Bytes().decode(z['pi_ids']),z['pi_text'])
                for i,w in enumerate(z['windows']):
                    self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                    self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,p),saved)
    def test_original_function_not_mutated(self):
        s,q,p=self.setup_case();tok=fixtures.Bytes()
        z=budget_control()(p,s,q,tok,budget=256,variant='diverse6')
        r.serialize(p,s,q,tok,budget=256)
        self.assertEqual(z,budget_control()(p,s,q,tok,budget=256,variant='diverse6'))
    def test_no_lexical_evidence_finite(self):
        props=[dict(code='return value',file='a.py',qualified='run')]
        self.assertEqual(r.relevance(props,''),[0.0])
        self.assertEqual(r.relevance([],''),[])
    def test_body_relevance(self):
        p=[dict(code='return zebraconfig(value)',file='a.py',qualified='run'),dict(code='return value',file='b.py',qualified='run')]
        a=r.relevance(p,'zebraconfig');self.assertGreater(a[0],a[1])
    def test_bad_config_rejected(self):
        s,q,p=self.setup_case()
        for cap,arm in [(192,'fused'),(256,'oracle')]:
            with self.assertRaises(ValueError):r.serialize(p,s,q,fixtures.Bytes(),budget=cap,variant=arm)

if __name__=='__main__':unittest.main()
