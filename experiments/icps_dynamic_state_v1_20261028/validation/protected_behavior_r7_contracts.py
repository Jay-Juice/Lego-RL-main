import copy
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import protected_behavior_r7 as p
from behavior_windows_r7_contracts import case,Bytes
from joint_windows_r7 import budget_control

class Contracts(unittest.TestCase):
    def fixture(self):
        s,c=case('def run(x):\n    y=x+1\n    if y:\n        return convert(y)\n    return 0\ndef convert(x):\n    return x+2\ndef other(x):\n    return x\n')
        return s,c,'`run` fails during convert(value)'
    def test_all3_protected_exact_control(self):
        s,c,q=self.fixture()
        for cap in (256,384):self.assertEqual(p.serialize(c,s,q,Bytes(),budget=cap,protected=3),budget_control()(c,s,q,Bytes(),budget=cap,variant='diverse6'))
    def test_source_cap_no_mutation_determinism(self):
        s,c,q=self.fixture();old=copy.deepcopy((s,c))
        for cap in (256,384):
            for count in (1,2):
                z=p.serialize(c,s,q,Bytes(),budget=cap,protected=count)
                self.assertEqual(z,p.serialize(c,s,q,Bytes(),budget=cap,protected=count))
                self.assertLessEqual(len(z['pi_ids']),cap);self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text']);self.assertLessEqual(len(z['windows']),3)
                for i,w in enumerate(z['windows']):
                    self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                    self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,c),old)
    def test_no_signals_exact(self):
        s,c,_=self.fixture()
        for count in (1,2):self.assertEqual(p.serialize(c,s,'unrelated prose',Bytes(),protected=count),budget_control()(c,s,'unrelated prose',Bytes(),budget=256,variant='diverse6'))
    def test_reject_bad(self):
        s,c,q=self.fixture()
        for v in (0,4,True):
            with self.assertRaises(ValueError):p.serialize(c,s,q,Bytes(),protected=v)

if __name__=='__main__':unittest.main()
