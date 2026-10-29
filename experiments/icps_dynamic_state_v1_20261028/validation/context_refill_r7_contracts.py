import copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import context_refill_r7 as r
import joint_context_r7_contracts as prior
from behavior_windows_r7_contracts import case,Bytes
from fast_allocation_r7 import serialize as baseline

class Contracts(unittest.TestCase):
    def test_exact_control(self):
        s,c=prior.Contracts().fixture()
        self.assertEqual(r.serialize(c,s,'compute y',Bytes(),arm='control1024_8'),baseline(c,s,'compute y',Bytes(),arm='fast1024_8'))
    def test_seed_preservation_cap_source_no_mutation(self):
        s,c=prior.Contracts().fixture();before=copy.deepcopy((s,c))
        for centered in (False,True):
            z=r.joint(c,s,'compute y',Bytes(),centered=centered);original=copy.deepcopy(z)
            x=r.refill(z,c,s,'compute y',Bytes())
            self.assertEqual(z,original);self.assertLessEqual(len(x['pi_ids']),1024)
            self.assertEqual(Bytes().decode(x['pi_ids']),x['pi_text'])
            for w in z['windows']:
                self.assertTrue(any(y['entity_id']==w['entity_id'] and y['start']<=w['start']<=w['end']<=y['end'] for y in x['windows']))
            for i,w in enumerate(x['windows']):
                self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                self.assertFalse(any(w['file']==y['file'] and max(w['start'],y['start'])<=min(w['end'],y['end']) for y in x['windows'][:i]))
        self.assertEqual((s,c),before)
    def test_refills_zero_query_context(self):
        s,c=case('def compute(x):\n'+''.join('    x=x+%d\n'%i for i in range(30))+'    return x\n')
        z=r.joint(c,s,'unrelated zzzyyy',Bytes());x=r.refill(z,c,s,'unrelated zzzyyy',Bytes())
        self.assertGreater(x['source_lines'],z['source_lines']);self.assertGreater(x['allocation_actions']['refill_steps'],0)
    def test_empty_invalid_unicode_and_fresh_snapshot(self):
        for arm in r.ARMS:
            self.assertTrue(r.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=arm)['unknown'])
        with self.assertRaises(ValueError):r.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm='oracle')
        s,c=case('def compute(x):\n    y=x+1 # 中文\n    return y\n')
        a=r.serialize(c,s,'compute',Bytes(),arm='joint_refill1024_8')
        self.assertEqual(Bytes().decode(a['pi_ids']),a['pi_text'])
        s['files']={p:t.replace('x+1','x-1') for p,t in s['files'].items()}
        b=r.serialize(c,s,'compute',Bytes(),arm='joint_refill1024_8')
        self.assertNotEqual(a['semantic_hash'],b['semantic_hash'])

if __name__=='__main__':unittest.main()
