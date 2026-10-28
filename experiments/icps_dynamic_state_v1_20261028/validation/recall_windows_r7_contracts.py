"""New source-only retrieval contracts, no development labels."""
import copy
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import recall_windows_r7 as r
import candidate_research_r7 as old
import candidate_research_r7_contracts as fixtures
from joint_windows_r7 import budget_control

class Contracts(unittest.TestCase):
    def test_baseline_exact(self):
        s=fixtures.Contracts().fixture();issue='process normalize Formatter render strip transform'
        a,inv=r.build(s,issue,task_uid='s',session_id='t');b,_=old.build(s,issue,task_uid='s',session_id='t')
        self.assertEqual(a['symbols12'],b['symbols12']);self.assertTrue(inv)
    def test_long_function_tail_is_searchable(self):
        text='def generic(value):\n'+''.join('    padding = value + 1\n' for _ in range(500))+'    return zebraconfig(value)\n'
        e=r.index.parse_file('a.py',text)[0];self.assertNotIn('zebraconfig',e['source'][:8192])
        self.assertEqual(r.passage_order([e],'zebraconfig')[0]['entity_id'],e['entity_id'])
    def test_limits_deterministic_no_mutation(self):
        s=dict(stable=True,files={f'mod{i}.py':''.join(f'def parse_{i}_{j}(value):\n    return value + {j}\n' for j in range(10)) for i in range(4)})
        before=copy.deepcopy(s);a,inv=r.build(s,'parse value',task_uid='s',session_id='t');b,inv2=r.build(s,'parse value',task_uid='s',session_id='t')
        self.assertEqual(a,b);self.assertEqual(inv,inv2);self.assertEqual(s,before)
        for mode,pool in a.items():
            self.assertEqual(len(pool),12 if mode=='symbols12' else 24)
            self.assertEqual(len({e['entity_id'] for e in pool}),len(pool))
        self.assertEqual(a['symbols24'][:12],a['symbols12'])
    def test_real_source_rendering_both_budgets(self):
        s=fixtures.Contracts().fixture();s['files']['pkg/unicode.py']='def clean(value):\n    return "你好" + value\n'
        pools,_=r.build(s,'clean normalize value',task_uid='s',session_id='t')
        for pool in pools.values():
            for cap in (256,384):
                z=budget_control()(pool,s,'clean normalize value',fixtures.Bytes(),budget=cap,variant='diverse6')
                self.assertLessEqual(len(z['pi_ids']),cap);self.assertEqual(fixtures.Bytes().decode(z['pi_ids']),z['pi_text'])
                for w in z['windows']:self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
    def test_empty_query_and_parse_fallback(self):
        self.assertEqual(r.passage_order([],''),[])
        a,_=r.build(dict(stable=True,files={'a.py':'def broken(\n return value'}),'broken value',task_uid='s',session_id='t')
        self.assertEqual(a['symbols12'][0]['syntax'],'parse_unavailable')
    def test_forbidden_unstable_rejected(self):
        for s in [dict(stable=False,files={'a.py':'x=1'}),dict(stable=True,files={'tests/a.py':'x=1'})]:
            with self.assertRaises(ValueError):r.build(s,'value',task_uid='s',session_id='t')

if __name__=='__main__':unittest.main()
