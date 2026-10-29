import copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import entity_allocation_r7 as e
from capacity_allocation_r7 import serialize as control,TokenCache
from behavior_windows_r7_contracts import case,Bytes

class Contracts(unittest.TestCase):
    def fixture(self):return case(''.join('def compute%d(x):\n    y=x+%d\n    return y\n'%(i,i) for i in range(12)))
    def test_control_exact(self):
        s,c=self.fixture()
        self.assertEqual(e.serialize(c,s,'compute y',Bytes(),arm='control512'),control(c,s,'compute y',Bytes(),arm='breadth512_6'))
    def test_rank_intervention(self):
        self.assertAlmostEqual(e.priority(23,0,'control512'),24**.5)
        self.assertEqual(e.priority(23,0,'flat512'),1)
        self.assertAlmostEqual(e.priority(23,1,'anchor2_flat512'),24**.5)
        self.assertEqual(e.priority(23,2,'anchor2_flat512'),1)
    def test_unique_tier(self):
        a={'entity_id':'a'};b={'entity_id':'b'}
        for mode in ('unique512','unique_flat512'):
            self.assertEqual(e.tier(a,[a],mode),1);self.assertEqual(e.tier(b,[a],mode),0)
        self.assertEqual(e.tier(a,[a],'control512'),0)
    def test_unique_entities_when_feasible(self):
        s,c=self.fixture()
        for mode in ('unique512','unique_flat512'):
            z=e.serialize(c,s,'compute y',Bytes(),arm=mode)
            self.assertEqual(len({w['entity_id'] for w in z['windows']}),6)
    def test_one_entity_repetition_fallback(self):
        s,c=case('def compute(x):\n'+''.join('    x=x+%d\n'%i for i in range(60))+'    return x\n')
        z=e.serialize(c,s,'compute x',Bytes(),arm='unique512')
        self.assertGreater(len(z['windows']),1)
    def test_full_source_caps_no_mutation_and_cache(self):
        s,c=self.fixture();before=copy.deepcopy((s,c));cache=TokenCache(Bytes())
        for mode in e.ARMS:
            z=e.serialize(c,s,'compute y',cache,arm=mode)
            self.assertEqual(z,e.serialize(c,s,'compute y',Bytes(),arm=mode))
            self.assertLessEqual(len(z['pi_ids']),512);self.assertLessEqual(len(z['windows']),6)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
            for i,w in enumerate(z['windows']):
                self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,c),before)
    def test_invalid_and_empty(self):
        s,c=self.fixture()
        with self.assertRaises(ValueError):e.serialize(c,s,'x',Bytes(),arm='oracle')
        for mode in e.ARMS:self.assertTrue(e.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=mode)['unknown'])

if __name__=='__main__':unittest.main()
