"""Synthetic source-only contracts; no coverage labels."""
import ast
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
import candidate_research_r7 as c
from budget_ablation_r7 import six_candidate_index
from window_research_r7 import serialize

class Bytes:
    def encode(self,text,**kwargs): return list(text.encode())
    def decode(self,ids,**kwargs): return bytes(ids).decode()

class Contracts(unittest.TestCase):
    def fixture(self):
        return dict(stable=True,limited=False,files={
            'pkg/a.py':'from .b import normalize as clean\n\ndef process(x):\n    return clean(x)\n\ndef other(x):\n    return process(x)\n',
            'pkg/b.py':'def normalize(x):\n    return x.strip()\n',
            'pkg/c.py':'class Formatter:\n    def render(self,x):\n        return self.clean(x)\n    def clean(self,x):\n        return str(x)\n',
            'pkg/d.py':'import pkg.b as tools\ndef transform(x):\n    return tools.normalize(x)\n'})
    def entities(self,s):return [e for p,t in s['files'].items() for e in c.index.parse_file(p,t)]
    def test_baseline_exact_and_payloads(self):
        s=self.fixture();issue='process normalize Formatter render strip transform'
        pools,stats=c.build(s,issue,task_uid='synthetic',session_id='test')
        old=six_candidate_index()(s,issue,task_uid='synthetic',session_id='test')
        self.assertEqual(pools['base6'],old['focus'])
        self.assertGreater(stats['static_edges'],0)
        for pool in pools.values():
            z=serialize(pool,s,issue,Bytes(),budget=256,variant='diverse6')
            self.assertLessEqual(len(z['pi_ids']),256)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
            for w in z['windows']:self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
    def test_static_imports_and_members(self):
        s=self.fixture();es=self.entities(s);names={e['entity_id']:e['file']+'::'+e['qualified'] for e in es}
        edges={(names[a],names[b]) for a,b in c.static_edges(es,s['files'])}
        self.assertIn(('pkg/a.py::process','pkg/b.py::normalize'),edges)
        self.assertIn(('pkg/d.py::transform','pkg/b.py::normalize'),edges)
        self.assertIn(('pkg/c.py::Formatter.render','pkg/c.py::Formatter.clean'),edges)
        self.assertIn(('pkg/a.py::other','pkg/a.py::process'),edges)
    def test_ambiguous_module_not_resolved(self):
        s=dict(files={'left/lib.py':'def target(x):\n    return x\n','right/lib.py':'def target(x):\n    return x\n','app.py':'from lib import target\ndef caller(x):\n    return target(x)\n'})
        self.assertEqual(c.static_edges(self.entities(s),s['files']),[])
    def test_bound_argument_not_call_edge(self):
        s=dict(files={'app.py':'def target(x):\n    return x\ndef caller(target,x):\n    return target(x)\n'})
        self.assertEqual(c.static_edges(self.entities(s),s['files']),[])
    def test_pool_bounds_determinism_and_anchors(self):
        s=dict(stable=True,files={f'mod{i}.py':''.join(f'def parse_{i}_{j}(value):\n    return value + {j}\n' for j in range(7)) for i in range(4)})
        a,_=c.build(s,'parse value',task_uid='s',session_id='t');b,_=c.build(s,'parse value',task_uid='s',session_id='t')
        self.assertEqual(a,b)
        for key,pool in a.items():
            self.assertEqual(len(pool),6 if key=='base6' else 12)
            self.assertEqual(len({e['entity_id'] for e in pool}),len(pool))
            self.assertEqual(pool[:3],a['base6'][:3])
    def test_unstable_and_forbidden_rejected(self):
        for s in [dict(stable=False,files={'a.py':'x=1'}),dict(stable=True,files={'tests/a.py':'x=1'})]:
            with self.assertRaises(ValueError):c.build(s,'value',task_uid='s',session_id='t')
    def test_parse_failure_explicit(self):
        s=dict(stable=True,files={'a.py':'def broken(\n return value'})
        pools,_=c.build(s,'broken value',task_uid='s',session_id='t')
        self.assertEqual(pools['base6'][0]['syntax'],'parse_unavailable')

if __name__=='__main__':unittest.main()
