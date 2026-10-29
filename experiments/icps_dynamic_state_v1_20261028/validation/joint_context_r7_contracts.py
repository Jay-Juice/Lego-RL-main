import copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import joint_context_r7 as j
from fast_allocation_r7 import serialize as baseline
from behavior_windows_r7_contracts import case,Bytes

class Contracts(unittest.TestCase):
    def fixture(self):
        return case(''.join('def compute%d(x):\n    y=x+%d\n    z=y*2\n    return z\n'%(i,i) for i in range(18)))
    def test_control_identity(self):
        s,c=self.fixture()
        self.assertEqual(j.serialize(c,s,'compute y',Bytes(),arm='control1024_8'),baseline(c,s,'compute y',Bytes(),arm='fast1024_8'))
    def test_caps_source_nonoverlap_no_mutation(self):
        s,c=self.fixture();before=copy.deepcopy((s,c))
        for arm in j.ARMS:
            z=j.serialize(c,s,'compute y',j.MeteredCache(Bytes()),arm=arm)
            self.assertLessEqual(len(z['pi_ids']),1024);self.assertLessEqual(len(z['windows']),8)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
            for i,w in enumerate(z['windows']):
                self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
            self.assertLessEqual(z.get('allocation_actions',{}).get('actions',0),64)
        self.assertEqual(before,(s,c))
    def test_centered_added_original_preserved(self):
        s,c=case('def compute(x):\n    a=x+1\n    signal=a+2\n    b=signal+3\n    return b\n')
        old=j.proposals(c,s,'signal',variant='flow_expand');new=j.centered_proposals(c,s,'signal')
        keys=lambda ws:{(w['entity_id'],w['start'],w['end']) for w in ws}
        self.assertTrue(keys(old)<=keys(new));self.assertTrue(keys(new)-keys(old))
        for w in new:
            if (w['entity_id'],w['start'],w['end']) in keys(new)-keys(old):self.assertLessEqual(w['end']-w['start']+1,3)
    def test_empty_invalid_unstable(self):
        for arm in j.ARMS:
            self.assertTrue(j.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=arm)['unknown'])
        with self.assertRaises(ValueError):j.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm='oracle')
        with self.assertRaises(ValueError):j.serialize([],dict(stable=False,files={}), 'x',Bytes(),arm='joint1024_8')
    def test_no_relevance_does_not_force_fill(self):
        s,c=case('def compute(x):\n'+''.join('    x=x+%d\n'%i for i in range(90))+'    return x\n')
        z=j.serialize(c,s,'unrelated zzzyyy',Bytes(),arm='joint1024_8')
        self.assertEqual(z['allocation_actions']['grow'],0)
        self.assertLess(len(z['pi_ids']),1024)
    def test_same_snapshot_repeat_and_changed_source(self):
        s,c=self.fixture()
        for arm in ('joint1024_8','joint_centered1024_8'):
            a=j.serialize(c,s,'compute y',Bytes(),arm=arm)
            self.assertEqual(a,j.serialize(c,s,'compute y',Bytes(),arm=arm))
            s2=copy.deepcopy(s);s2['files']={p:t.replace('y=x+','y=x-') for p,t in s['files'].items()}
            b=j.serialize(c,s2,'compute y',Bytes(),arm=arm)
            self.assertNotEqual(a['semantic_hash'],b['semantic_hash'])
    def test_unicode_and_long_unfittable_lines(self):
        s,c=case('def compute(x):\n    y="'+('中'*800)+'"\n    return x\n')
        for arm in j.ARMS:
            z=j.serialize(c,s,'compute',Bytes(),arm=arm)
            self.assertLessEqual(len(z['pi_ids']),1024)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])

if __name__=='__main__':unittest.main()
