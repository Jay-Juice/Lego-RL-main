import copy
import sys
import unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import capacity_allocation_r7 as c
from joint_windows_r7 import budget_control
from behavior_windows_r7_contracts import case, Bytes


class Contracts(unittest.TestCase):
    def fixture(self):
        return case(''.join('def compute%d(x):\n    y=x+%d\n    return y\n' % (i,i) for i in range(12)))

    def test_control_exact(self):
        s,p=self.fixture()
        for cap in (256,384):
            self.assertEqual(c.serialize(p,s,'compute y',Bytes(),arm=f'base{cap}_3'),
                budget_control()(p,s,'compute y',Bytes(),budget=cap,variant='diverse6'))

    def test_append_preserves_final_windows_and_payload(self):
        s,p=self.fixture()
        base=c.serialize(p,s,'compute y',Bytes(),arm='base256_3')
        self.assertTrue(base['windows'])
        for arm in ('append512_6','append768_6'):
            z=c.serialize(p,s,'compute y',Bytes(),arm=arm)
            self.assertEqual(z['windows'][:len(base['windows'])],base['windows'])
            self.assertTrue(z['pi_text'].startswith(base['pi_text']))
            self.assertGreater(len(z['windows']),len(base['windows']))

    def test_six_slot_intervention_actually_uses_extra_slots(self):
        s,p=self.fixture()
        z=c.serialize(p,s,'compute y',Bytes(),arm='breadth768_6')
        self.assertGreater(len(z['windows']),3)

    def test_source_caps_nonoverlap_no_mutation(self):
        s,p=self.fixture();before=copy.deepcopy((s,p))
        for arm,(cap,slots,_) in c.ARMS.items():
            z=c.serialize(p,s,'compute y',Bytes(),arm=arm)
            self.assertLessEqual(len(z['pi_ids']),cap)
            self.assertLessEqual(len(z['windows']),slots)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
            for i,w in enumerate(z['windows']):
                self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,p),before)

    def test_cache_exact_and_defensive_copy(self):
        t=c.TokenCache(Bytes());s,p=self.fixture()
        for arm in c.ARMS:
            self.assertEqual(c.serialize(p,s,'compute',t,arm=arm),c.serialize(p,s,'compute',Bytes(),arm=arm))
        a=t.encode('abc');a.clear();self.assertEqual(t.encode('abc'),Bytes().encode('abc'))

    def test_reject_invalid_and_empty(self):
        s,p=self.fixture()
        with self.assertRaises(ValueError):c.serialize(p,s,'x',Bytes(),arm='unbounded')
        s['stable']=False
        with self.assertRaises(ValueError):c.serialize(p,s,'x',Bytes(),arm='base768_3')
        for arm in c.ARMS:
            z=c.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=arm)
            self.assertTrue(z['unknown']);self.assertLessEqual(len(z['pi_ids']),c.ARMS[arm][0])


if __name__=='__main__':unittest.main()
