"""Source-only synthetic contracts for the isolated joint allocator."""
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core')]
from joint_windows_r7 import Allocator,close_range,budget_control
from window_research_r7 import serialize as old
from issue_program_state import build_initial_index

class Bytes:
    def encode(self,text,**kwargs):return list(text.encode())
    def decode(self,ids,**kwargs):return bytes(ids).decode()

class Contracts(unittest.TestCase):
    def fixture(self):
        s=dict(stable=True,limited=False,files={'app.py':'def normalize(value):\n    result = (\n        value.strip()\n        .lower()\n    )\n    return result\n\ndef fallback(value):\n    return "默认" if value is None else value\n'})
        issue='normalize value strip lower result fallback'
        c=build_initial_index(s,issue,task_uid='synthetic',session_id='joint')['focus']
        return s,issue,c
    def test_real_source_caps_roundtrip(self):
        s,issue,c=self.fixture();a=Allocator(c,s,issue,Bytes())
        for cap in (256,384):
            for coherent in (False,True):
                z=a.serialize(budget=cap,coherent=coherent)
                self.assertLessEqual(len(z['pi_ids']),cap);self.assertLessEqual(len(z['windows']),3)
                self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
                for w in z['windows']:self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
    def test_joint_search_escapes_expensive_first_choice(self):
        a=Allocator([],dict(stable=True,files={}), 'query',Bytes())
        ws=[dict(entity_id=str(i),rank=i,file=str(i)+'.py',start=1,end=3,value=value,cost=cost) for i,(value,cost) in enumerate([(10,170),(7,110),(7,110)])]
        a.bank=lambda coherent:ws;a.cost=lambda xs:20+sum(x['cost'] for x in xs);a.objective=lambda xs:sum(x['value'] for x in xs)
        chosen=a.search(256,False)
        self.assertEqual({w['entity_id'] for w in chosen},{'1','2'})
    def test_no_overlap_through_different_entities(self):
        a=dict(file='x.py',start=3,end=8);b=dict(file='x.py',start=7,end=12)
        self.assertFalse(Allocator.admissible([a],b))
        self.assertTrue(Allocator.admissible([a],dict(b,file='y.py')))
    def test_short_multiline_closure(self):
        self.assertEqual(close_range(3,4,{},[(2,5),(6,6)]),(2,5))
        self.assertEqual(close_range(3,4,{},[(1,100)]),(3,4))
    def test_complete_small_entity_offered(self):
        s,issue,c=self.fixture();a=Allocator(c,s,issue,Bytes())
        # Closure preserves the original statement's exact text and full entity
        # can be considered; candidate pruning remains bounded.
        bank=a.bank(True)
        self.assertLessEqual(len(bank),7*len(c))
        self.assertTrue(any(w['start']==1 and w['end']==6 for w in bank))
    def test_original_control_exact_and_384(self):
        s,issue,c=self.fixture()
        self.assertEqual(budget_control()(c,s,issue,Bytes(),budget=256,variant='diverse6'),old(c,s,issue,Bytes(),budget=256,variant='diverse6'))
        self.assertLessEqual(len(budget_control()(c,s,issue,Bytes(),budget=384,variant='diverse6')['pi_ids']),384)
    def test_deterministic_and_no_mutation(self):
        import copy
        s,issue,c=self.fixture();before=copy.deepcopy((s,c));a=Allocator(c,s,issue,Bytes())
        self.assertEqual(a.serialize(coherent=True),Allocator(c,s,issue,Bytes()).serialize(coherent=True))
        self.assertEqual(before,(s,c))
    def test_parse_failure_empty_and_rejections(self):
        s=dict(stable=True,files={'broken.py':'def broken(\n return value'})
        c=build_initial_index(s,'broken value',task_uid='s',session_id='t')['focus']
        z=Allocator(c,s,'broken value',Bytes()).serialize(coherent=True)
        self.assertTrue(all(w['syntax']=='parse_unavailable' for w in z['windows']))
        self.assertTrue(Allocator([],dict(stable=True,files={}), 'missing',Bytes()).serialize()['unknown'])
        with self.assertRaises(ValueError):Allocator([],dict(stable=False,files={}), '',Bytes())
        with self.assertRaises(ValueError):Allocator([],dict(stable=True,files={}), '',Bytes()).serialize(budget=512)

if __name__=='__main__':unittest.main()
