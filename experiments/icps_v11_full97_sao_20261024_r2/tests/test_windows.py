import copy,json,pathlib,sys,unittest,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/os.environ.get('ICPS_V11_SOURCE_DIR','src')))
from window_serializer import *
class TinyTokenizer:
    def encode(self,x,add_special_tokens=False):return list(x.encode())
class Windows(unittest.TestCase):
    def setUp(self):
        self.t=TinyTokenizer();self.c=[dict(file='p.py',qualified='f',entity_id='1',start_line=1,end_line=7,kind='function')]
        self.s=dict(stable=True,limited=False,files={'p.py':'def f(x):\n    a = x\n    b = 2\n    limit = x + b\n    print(limit)\n    z = 3\n    return z\n'})
    def ser(self,**kw):return serialize(self.c,self.s,'`limit` calculation',self.t,**kw)
    def test_budget(self):
        for b in (0,24,128,192,256):self.assertLessEqual(len(self.ser(budget=b)['pi_ids']),b)
    def test_source(self):
        for w in self.ser()['windows']:self.assertEqual(w['code'],''.join(self.s['files']['p.py'].splitlines(True)[w['start']-1:w['end']]))
    def test_query(self):self.assertGreater(proposals(self.c,self.s['files'],'`limit`')[0]['score'],0)
    def test_control_issue_independent(self):
        a=serialize(self.c,self.s,'limit',self.t,control=True);b=serialize(self.c,self.s,'other',self.t,control=True)
        self.assertEqual(a['pi_ids'],b['pi_ids'])
    def test_deterministic(self):self.assertEqual(self.ser()['pi_ids'],self.ser()['pi_ids'])
    def test_label_swap_no_input(self):
        label={'line':4};a=self.ser();label={'line':1};self.assertEqual(a['pi_ids'],self.ser()['pi_ids'])
    def session(self):return WindowSession(self.c,'limit',self.t,'t','s')
    def cap(self,w,s,n):return w.capture(s,task_uid='t',session_id='s',logical_call_id=str(n),seq=n)
    def test_unchanged(self):
        w=self.session();self.cap(w,self.s,0);self.assertEqual(self.cap(w,self.s,1)['pi_ids'],[])
    def test_unrelated(self):
        w=self.session();self.cap(w,self.s,0);s=copy.deepcopy(self.s);s['files']['other.py']='x=3';self.assertEqual(self.cap(w,s,1)['pi_ids'],[])
    def test_other_function_in_same_file(self):
        w=self.session();self.cap(w,self.s,0);s=copy.deepcopy(self.s);s['files']['p.py']+='\ndef unrelated():\n    return 3\n';self.assertEqual(self.cap(w,s,1)['pi_ids'],[])
    def test_exhaustion_explicit(self):
        w=self.session();self.cap(w,self.s,0);w.remaining=64
        s=copy.deepcopy(self.s);s['files']['p.py']=s['files']['p.py'].replace('x + b','x - b')
        self.assertIn('exhausted',self.cap(w,s,1)['pi_text']);self.assertEqual(self.cap(w,self.s,2)['pi_ids'],[])
    def test_edit_revert(self):
        w=self.session();self.cap(w,self.s,0);s=copy.deepcopy(self.s);s['files']['p.py']=s['files']['p.py'].replace('x + b','x - b')
        self.assertIn('x - b',self.cap(w,s,1)['pi_text']);self.assertTrue(self.cap(w,self.s,2)['pi_ids'])
    def test_delete(self):
        w=self.session();self.cap(w,self.s,0);s=copy.deepcopy(self.s);s['files']={};self.assertTrue(self.cap(w,s,1)['unknown'])
    def test_parse(self):
        s=copy.deepcopy(self.s);s['files']['p.py']='def f(:\n x = 1\n';r=serialize(self.c,s,'f',self.t,budget=256);self.assertIn('parse?',r['pi_text'])
    def test_unstable(self):
        s=copy.deepcopy(self.s);s['stable']=False;self.assertTrue(serialize(self.c,s,'f',self.t)['unknown'])
    def test_cross_session(self):
        with self.assertRaises(ValueError):self.session().capture(self.s,task_uid='other',session_id='s',logical_call_id='0',seq=0)
    def test_retry_changed(self):
        w=self.session();self.cap(w,self.s,0);s=copy.deepcopy(self.s);s['files']['p.py']=s['files']['p.py'].replace('x + b','x - b')
        with self.assertRaises(ValueError):self.cap(w,s,0)
    def test_release(self):
        w=self.session();self.cap(w,self.s,0);w.release();self.assertEqual(w.retries,{});self.assertEqual(w.candidates,[])
    def test_unicode(self):
        s=copy.deepcopy(self.s);s['files']['p.py']=s['files']['p.py'].replace('a = x','a = "中文"');r=serialize(self.c,s,'中文',self.t,budget=256);self.assertLessEqual(len(r['pi_ids']),256)
    def test_candidates_untouched(self):
        c=copy.deepcopy(self.c);self.ser();self.assertEqual(c,self.c)
if __name__=='__main__':unittest.main()
