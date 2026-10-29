import copy
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import behavior_windows_r7 as b
import issue_program_state as idx
from joint_windows_r7 import budget_control
from candidate_research_r7_contracts import Bytes

def case(text):
    s=dict(stable=True,files={'pkg/a.py':text})
    return s,idx.parse_file('pkg/a.py',text)

class Contracts(unittest.TestCase):
    def test_issue_symbol_sources(self):
        q='method parse; `Frame.normalize` fails; File a.py, line 9, in transform; helper(value)'
        self.assertTrue({'parse','normalize','transform','helper'}<=b.issue_symbols(q))
    def test_named_entity_one_hop_not_two(self):
        s,p=case('def run(x):\n    return helper(x)\ndef helper(x):\n    return tail(x)\ndef tail(x):\n    return x\n')
        _,c,_=b.signals(p,s,'`run` fails')
        self.assertEqual([c[e['entity_id']]['prior'] for e in p],[.5,.35,0])
    def test_ambiguous_callee_not_promoted(self):
        s,p=case('def run(x):\n    return helper(x)\nclass A:\n    def helper(self,x):\n        return x\nclass B:\n    def helper(self,x):\n        return x\n')
        _,c,_=b.signals(p,s,'`run` fails')
        for e in p:
            if e['qualified'].endswith('.helper'):self.assertEqual(c[e['entity_id']]['prior'],0)
    def test_nearest_store_and_guard(self):
        s,p=case('def run(x):\n    y=x+1\n    y=x+2\n    if y:\n        z=convert(y)\n        return z\n')
        _,c,_=b.signals(p,s,'convert(value) fails');v=c[p[0]['entity_id']]['lines']
        self.assertNotIn(2,v);self.assertGreater(v[3],0);self.assertGreater(v[4],0);self.assertGreater(v[5],0);self.assertGreater(v[6],0)
    def test_nested_scope_not_propagated(self):
        s,p=case('def outer(x):\n    y=x\n    def inner(x):\n        return convert(y)\n    return x\n')
        _,c,_=b.signals(p,s,'convert(value) fails')
        self.assertEqual(c[p[0]['entity_id']]['lines'],{})
    def test_literal_message_not_docstring(self):
        s,p=case('def fail():\n    """the very specific error text"""\n    raise ValueError("the very specific error text")\n')
        _,c,_=b.signals(p,s,'the very specific error text');v=c[p[0]['entity_id']]['lines']
        self.assertNotIn(2,v);self.assertIn(3,v)
    def test_no_signal_exact_baseline(self):
        s,p=case('def run(value):\n    value=value+1\n    return value\n')
        for cap in (256,384):
            for arm in ('rank','extend'):
                self.assertEqual(b.serialize(p,s,'unrelated prose',Bytes(),budget=cap,variant=arm),budget_control()(p,s,'unrelated prose',Bytes(),budget=cap,variant='diverse6'))
    def test_original_seed_bank_preserved(self):
        s,p=case('def run(x):\n    y=x+1\n'+''.join('    a%d=alpha+beta+gamma+delta+epsilon+zeta\n'%i for i in range(30))+'    z=convert(y)\n')
        old=b.proposals(p,s,'alpha beta gamma delta epsilon zeta convert(y) fails',variant='flow_expand')
        new,_,_=b.prepare(p,s,'alpha beta gamma delta epsilon zeta convert(y) fails',extend=True)
        self.assertEqual(new[:len(old)],old)
        self.assertGreater(len(new),len(old))
    def test_actual_source_no_mutation_caps(self):
        s,p=case('def run(x):\n    y=x+1\n    if y:\n        return convert(y)\n    return "你好"\n');prior=copy.deepcopy((s,p))
        for cap in (256,384):
            for arm in ('rank','extend'):
                z=b.serialize(p,s,'convert(value) fails',Bytes(),budget=cap,variant=arm)
                self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text']);self.assertLessEqual(len(z['pi_ids']),cap);self.assertLessEqual(len(z['windows']),3)
                for i,w in enumerate(z['windows']):
                    self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                    self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,p),prior)
    def test_invalid_snapshot_and_config(self):
        s,p=case('def run(x):\n    return x\n')
        for cap,arm in [(192,'rank'),(256,'oracle')]:
            with self.assertRaises(ValueError):b.serialize(p,s,'x',Bytes(),budget=cap,variant=arm)
        s['stable']=False
        with self.assertRaises(ValueError):b.serialize(p,s,'x',Bytes())

if __name__=='__main__':unittest.main()
