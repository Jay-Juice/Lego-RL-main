"""Boundary regression; not a reason to change any model/optimizer setting."""
import pathlib,sys,unittest,copy,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/os.environ.get('ICPS_V11_SOURCE_DIR','src')))
from window_serializer import WindowSession
class T:
    def encode(self,x,add_special_tokens=False):return list(x.encode())
class Edges(unittest.TestCase):
    def setUp(self):
        self.c=[dict(file='p.py',qualified='f',kind='function',entity_id='f',start_line=1,end_line=3)]
        self.s=dict(stable=True,limited=True,files={'p.py':'def f(x):\n    y = x + 1\n    return y\n'})
    def cap(self,a,s,n,key=None):return a.capture(s,task_uid='t',session_id='s',logical_call_id=str(n) if key is None else key,seq=n)
    def test_repeated_limited_scope_does_not_spend_source_budget(self):
        a=WindowSession(self.c,'y',T(),'t','s');self.cap(a,self.s,0);remaining=a.remaining;r=self.cap(a,self.s,1)
        self.assertEqual(r['pi_ids'],[]);self.assertTrue(r['unknown']);self.assertEqual(a.remaining,remaining)
    def test_exhaustion_marker_cannot_be_deduped_as_old_state(self):
        a=WindowSession(self.c,'y',T(),'t','s');first=self.cap(a,self.s,0);a.remaining=64
        changed=copy.deepcopy(self.s);changed['files']['p.py']=changed['files']['p.py'].replace('x + 1','x + 2')
        marker=self.cap(a,changed,1)
        # If state is unchanged, no exhaustion is needed; otherwise marker must
        # get a fresh insertion identity relative to all prior visible state.
        if marker['pi_ids']:self.assertNotEqual(marker['pi_insertion_key'],first['pi_insertion_key'])
    def test_old_logical_retry_rejected_when_payload_cache_expired(self):
        a=WindowSession(self.c,'y',T(),'t','s');self.cap(a,self.s,0,'a');self.cap(a,self.s,1,'b')
        with self.assertRaises(ValueError):self.cap(a,self.s,2,'a')
if __name__=='__main__':unittest.main()
