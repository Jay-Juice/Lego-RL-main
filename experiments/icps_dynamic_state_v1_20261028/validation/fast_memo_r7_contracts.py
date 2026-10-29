import copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import fast_memo_r7 as m
import fast_allocation_r7 as f
from behavior_windows_r7_contracts import case,Bytes

class Contracts(unittest.TestCase):
    def test_exact_multi_entity(self):
        s,c=case(''.join('def run%d(x):\n    y=x+%d\n    return y\n'%(i,i) for i in range(20)))
        for arm in ('fast768_8','fast1024_12'):
            self.assertEqual(m.serialize(c,s,'run y',f.MeteredCache(Bytes()),arm=arm),f.serialize(c,s,'run y',f.MeteredCache(Bytes()),arm=arm))
    def test_exact_long_and_unicode(self):
        s,c=case('def run(x):\n'+''.join('    x=x+%d # 中文\n'%i for i in range(70))+'    return x\n')
        before=copy.deepcopy((s,c))
        for arm in ('fast768_8','fast1024_12'):
            self.assertEqual(m.serialize(c,s,'run x',f.MeteredCache(Bytes()),arm=arm),f.serialize(c,s,'run x',f.MeteredCache(Bytes()),arm=arm))
        self.assertEqual((s,c),before)
    def test_no_cache_survives_edit(self):
        s,c=case('def run(x):\n    return x+1\n')
        old=m.serialize(c,s,'run',Bytes(),arm='fast768_8')
        s['files']['pkg/a.py']='def run(x):\n    return x+2\n'
        new=m.serialize(c,s,'run',Bytes(),arm='fast768_8')
        self.assertNotEqual(old['pi_text'],new['pi_text'])
        self.assertEqual(new,f.serialize(c,s,'run',Bytes(),arm='fast768_8'))
    def test_globals_and_empty(self):
        import window_research_r7 as w
        prior=w.terms
        for arm in ('fast768_8','fast1024_12'):
            self.assertEqual(m.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=arm),f.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm=arm))
        self.assertIs(w.terms,prior)

if __name__=='__main__':unittest.main()
