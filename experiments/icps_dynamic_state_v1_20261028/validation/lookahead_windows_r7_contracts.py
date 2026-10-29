"""Synthetic selection-only contracts before any follow-up scoring."""
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import joint_windows_r7_contracts as fixtures
Bytes=fixtures.Bytes
from lookahead_windows_r7 import choose,serialize

class Contracts(unittest.TestCase):
    def test_greedy_trap_with_original_utility(self):
        # First option has highest local score/sqrt(cost), but two smaller
        # independent windows have a greater sum of unchanged utilities.
        props=[dict(entity_id=str(i),rank=0,file=f'{i}.py',start=1,end=3,score=score,code='query',cost=cost) for i,(score,cost) in enumerate([(12,170),(8,110),(8,110)])]
        result=choose(props,lambda ws:20+sum(w['cost'] for w in ws),256,set())
        self.assertEqual({w['entity_id'] for w in result},{'1','2'})
    def test_actual_source_caps_and_determinism(self):
        s,issue,c=fixtures.Contracts().fixture()
        for cap in (256,384):
            a=serialize(c,s,issue,Bytes(),budget=cap);b=serialize(c,s,issue,Bytes(),budget=cap)
            self.assertEqual(a,b);self.assertLessEqual(len(a['pi_ids']),cap)
            self.assertEqual(Bytes().decode(a['pi_ids']),a['pi_text'])
            for w in a['windows']:self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
    def test_original_residual_expansion_function_body_preserved(self):
        import inspect,textwrap
        import lookahead_windows_r7 as l
        original=textwrap.dedent(inspect.getsource(l.old_serialize))
        # Serializer's globals are copied: the original runtime function is not
        # replaced. Shared helpers remain the exact original function objects.
        new=l.serializer();self.assertIsNot(new,l.old_serialize)
        for key in ['resolve','proposals','render','marginal_score']:self.assertIs(new.__globals__[key],l.old_serialize.__globals__[key])
        self.assertIn('while chosen and variant',original)
    def test_empty_and_overlap(self):
        self.assertEqual(choose([],lambda ws:0,256,set()),[])
        props=[dict(entity_id=str(i),rank=i,file='a.py',start=1,end=3,score=5,code='query') for i in range(2)]
        self.assertEqual(len(choose(props,lambda ws:len(ws)*20,256,{'query'})),1)

if __name__=='__main__':unittest.main()
