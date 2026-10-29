import ast,copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import scope_windows_r7 as s
from entity_evidence_r7_contracts import BatchBytes
from behavior_windows_r7_contracts import case
from window_serializer import resolve

class Contracts(unittest.TestCase):
    def fixture(self):
        return case('class Worker:\n    flag = 1\n'+''.join('    def method%d(self,x):\n        y=x+%d\n        return y\n'%(i,i) for i in range(14)))
    def test_control_exact(self):
        snap,c=self.fixture()
        self.assertEqual(s.serialize(c,snap,'x y',BatchBytes(),arm='control1024_8'),
                         s.base.serialize(c,snap,'x y',BatchBytes(),arm='cached1024_8'))
    def test_partition_complete_disjoint(self):
        snap,c=self.fixture();e=next(e for e in resolve(c,snap['files']) if isinstance(e['node'],ast.ClassDef))
        spans=list(s.units(e));lines=[i for lo,hi,_,_ in spans for i in range(lo,hi+1)]
        self.assertEqual(lines,list(range(e['start_line'],e['end_line']+1)))
        self.assertEqual(len(spans),15)
    def test_nested_class_decorators_and_gaps(self):
        snap,c=case('class A:\n    x=1\n    @staticmethod\n    def f():\n        return 1\n    class B:\n        y=2\n        def g(self):\n            return 3\n    z=4\n')
        e=resolve(c,snap['files'])[0];u=list(s.units(e))
        self.assertEqual([i for a,b,_,_ in u for i in range(a,b+1)],list(range(1,11)))
        self.assertTrue(any(a==3 and name=='A.f' for a,b,name,n in u))
    def test_caps_exact_source_scoped_growth(self):
        snap,c=self.fixture();prior=copy.deepcopy((snap,c))
        for arm in s.ARMS:
            z=s.serialize(c,snap,'method x y',s.MeteredCache(BatchBytes()),arm=arm)
            self.assertLessEqual(len(z['pi_ids']),1024);self.assertLessEqual(len(z['windows']),8)
            for i,w in enumerate(z['windows']):
                self.assertEqual(w['code'],''.join(snap['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                if arm!='control1024_8':self.assertTrue(w['scope_start']<=w['start']<=w['end']<=w['scope_end'])
                self.assertFalse(any(w['file']==v['file'] and max(w['start'],v['start'])<=min(w['end'],v['end']) for v in z['windows'][:i]))
        self.assertEqual(prior,(snap,c))
    def test_bounded_proposals_and_method_breadth(self):
        snap,c=self.fixture();entities=resolve(c[:1],snap['files'])
        props=s.scope_proposals(entities,snap['files'],'x',balanced=True)
        self.assertLessEqual(len(props),36)
        self.assertEqual(len({w['scope_qualified'] for w in props}),15)
        self.assertTrue(all(w['entity_id']==c[0]['entity_id'] for w in props))
    def test_same_owner_across_parent_and_child(self):
        snap,c=self.fixture();entities=resolve(c,snap['files'])
        props=s.scope_proposals(entities,snap['files'],'x',balanced=True)
        pair=[w for w in props if w['scope_qualified']=='Worker.method0']
        self.assertGreater(len({w['entity_id'] for w in pair}),1)
        self.assertEqual(len({s.scope_key(w) for w in pair}),1)
    def test_fresh_snapshot_and_no_global_mutation(self):
        snap,c=self.fixture();original=s.base.serialize
        a=s.serialize(c,snap,'y',BatchBytes(),arm='scope1024_8')
        snap['files']={p:v.replace('y=x+','y=x-') for p,v in snap['files'].items()}
        b=s.serialize(c,snap,'y',BatchBytes(),arm='scope1024_8')
        self.assertNotEqual(a['semantic_hash'],b['semantic_hash']);self.assertIs(original,s.base.serialize)
    def test_empty_invalid_unstable(self):
        for arm in s.ARMS:self.assertTrue(s.serialize([],dict(stable=True,files={}), 'x',BatchBytes(),arm=arm)['unknown'])
        with self.assertRaises(ValueError):s.serialize([],dict(stable=True,files={}), 'x',BatchBytes(),arm='oracle')
        with self.assertRaises(ValueError):s.serialize([],dict(stable=False,files={}), 'x',BatchBytes(),arm='scope1024_8')

if __name__=='__main__':unittest.main()
