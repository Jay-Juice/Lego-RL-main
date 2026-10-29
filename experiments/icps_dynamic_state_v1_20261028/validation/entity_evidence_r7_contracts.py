import copy,sys,unittest
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import entity_evidence_r7 as e
from behavior_windows_r7_contracts import case,Bytes
from fast_allocation_r7 import serialize as baseline
from window_serializer import resolve

class BatchBytes(Bytes):
    def __call__(self,texts,**kwargs):return {'input_ids':[self.encode(x) for x in texts]}

class Contracts(unittest.TestCase):
    def fixture(self):return case(''.join('def compute%d(x):\n    y=x+%d # 中文\n    return y\n'%(i,i) for i in range(18)))
    def test_exact_cached_output(self):
        for s,c in [self.fixture(),case('def run(x):\n'+''.join('    x=x+%d\n'%i for i in range(70))+'    return x\n')]:
            for issue in ['compute y','unrelated words','`run` fails']:
                a=baseline(c,s,issue,Bytes(),arm='fast1024_8')
                tok=e.MeteredCache(BatchBytes());b=e.serialize(c,s,issue,tok,arm='cached1024_8')
                self.assertEqual(a,b);self.assertGreater(tok.backend_batches,0)
    def test_batch_exact_and_unique(self):
        t=e.MeteredCache(BatchBytes());t.prefetch(['abc','abc','中x']);t.prefetch(['abc'])
        self.assertEqual(t.encode('中x',add_special_tokens=False),Bytes().encode('中x'))
        self.assertEqual(t.backend_batches,1);self.assertEqual(t.misses,2)
        self.assertEqual(t.encoded_bytes,len('abc中x'.encode()))
    def test_caps_source_no_mutation(self):
        s,c=self.fixture();old=copy.deepcopy((s,c))
        for arm in e.ARMS:
            z=e.serialize(c,s,'compute y',e.MeteredCache(BatchBytes()),arm=arm)
            self.assertLessEqual(len(z['pi_ids']),1024);self.assertLessEqual(len(z['windows']),8)
            self.assertEqual(Bytes().decode(z['pi_ids']),z['pi_text'])
            for i,w in enumerate(z['windows']):
                self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                self.assertFalse(any(w['file']==x['file'] and max(w['start'],x['start'])<=min(w['end'],x['end']) for x in z['windows'][:i]))
        self.assertEqual((s,c),old)
    def test_own_scope_and_docstring_excluded(self):
        s,c=case('def outer(x):\n    """docword"""\n    def inner():\n        return hiddenword\n    return visibleword\n')
        docs,*_=e.evidence(resolve(c,s['files']),'docword hiddenword visibleword')
        self.assertEqual(docs[c[0]['entity_id']],{'visibleword'})
    def test_unique_explicit_and_rare_evidence(self):
        s,c=case('def convert(x):\n    return rare(x)\ndef helper(x):\n    return common(x)\n')
        docs,w,support,exact,scale=e.evidence(resolve(c,s['files']),'`convert` rare common')
        self.assertEqual(exact,{c[0]['entity_id']});self.assertGreater(support[c[0]['entity_id']],support[c[1]['entity_id']])
        self.assertTrue(all(0<=x<=1 for x in support.values()))
    def test_no_evidence_exact(self):
        s,c=self.fixture()
        for arm in ('entity1024_8','complement1024_8'):
            self.assertEqual(e.serialize(c,s,'zzzzunknown',BatchBytes(),arm=arm),baseline(c,s,'zzzzunknown',Bytes(),arm='fast1024_8'))
    def test_snapshot_cache_not_stale(self):
        s,c=self.fixture();a=e.serialize(c,s,'compute',BatchBytes(),arm='cached1024_8')
        s['files']={p:v.replace('y=x+','y=x-') for p,v in s['files'].items()}
        b=e.serialize(c,s,'compute',BatchBytes(),arm='cached1024_8');self.assertNotEqual(a['semantic_hash'],b['semantic_hash'])
    def test_empty_invalid_unstable(self):
        for arm in e.ARMS:self.assertTrue(e.serialize([],dict(stable=True,files={}), 'x',BatchBytes(),arm=arm)['unknown'])
        with self.assertRaises(ValueError):e.serialize([],dict(stable=True,files={}), 'x',Bytes(),arm='oracle')
        with self.assertRaises(ValueError):e.serialize([],dict(stable=False,files={}), 'x',Bytes(),arm='cached1024_8')

if __name__=='__main__':unittest.main()
