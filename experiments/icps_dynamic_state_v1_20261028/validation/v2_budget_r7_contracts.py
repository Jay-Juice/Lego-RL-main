import copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import v2_budget_r7 as f
from behavior_windows_r7_contracts import case,Bytes

class Contracts(unittest.TestCase):
    def fixture(self):return case(''.join('def compute%d(x):\n    y=x+%d\n    return y\n'%(i,i) for i in range(18)))
    def test_additive_tokenizer_exact_control(self):
        s,c=self.fixture()
        from fast_allocation_r7 import serialize as baseline
        self.assertEqual(f.serialize(c,s,'compute y',Bytes(),arm='control1024_8'),baseline(c,s,'compute y',Bytes(),arm='fast1024_8'))
    def test_meter_independent(self):
        a=f.MeteredCache(Bytes());b=f.MeteredCache(Bytes())
        a.encode('abc');a.encode('abc');b.encode('abc')
        self.assertEqual(a.stats(),dict(encode_requests=2,encode_misses=1,encoded_bytes=3))
        self.assertEqual(b.requests,1)
    def test_caps_source_no_mutation(self):
        s,c=self.fixture();before=copy.deepcopy((s,c))
        for arm,(cap,slots,_) in f.ARMS.items():
            z=f.serialize(c,s,'compute y',f.MeteredCache(Bytes()),arm=arm)
            self.assertLessEqual(len(z['pi_ids']),cap);self.assertLessEqual(len(z['windows']),slots)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
            for i,w in enumerate(z['windows']):
                self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,c),before)
    def test_failed_first_shortlist_scans_later(self):
        props=[dict(file='a',start=i,end=i,entity_id=str(i),rank=0,code='x',score=100-i) for i in range(12)]
        text=lambda ws:''.join('a:'+w['code'] for w in ws)
        cost=lambda ws:999 if ws[-1]['start']<8 else 5
        out=f.candidate_order(props,[],set(),{'x'},text,cost,Bytes(),10,'diverse6')
        self.assertEqual([i for i,_ in out],[8,9,10,11])
    def test_exact_cost_not_approximate_is_admission(self):
        w=dict(file='a',start=1,end=1,entity_id='a',rank=0,code='x'*30,score=1)
        out=f.candidate_order([w],[],set(),{'x'},lambda ws:'a:'+''.join(x['code'] for x in ws),lambda ws:1,Bytes(),2,'diverse6')
        self.assertEqual(out,[(0,w)])
    def test_one_entity_and_unicode(self):
        s,c=case('def compute(x):\n'+''.join('    x=x+%d # 中文\n'%i for i in range(40))+'    return x\n')
        for arm in ('fast1920_8','fast2048_8'):
            z=f.serialize(c,s,'compute x',f.MeteredCache(Bytes()),arm=arm)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text']);self.assertTrue(z['windows'])
    def test_empty_invalid_unstable(self):
        for arm in f.ARMS:
            self.assertTrue(f.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=arm)['unknown'])
        with self.assertRaises(ValueError):f.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm='oracle')
        with self.assertRaises(ValueError):f.serialize([],dict(stable=False,files={}), 'x',Bytes(),arm='fast1920_8')

if __name__=='__main__':unittest.main()
