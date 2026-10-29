import copy,pathlib,sys,unittest
F=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(F/'src'),str(F/'core')]
import dense_state as d

class Tok:
    def encode(self,text,add_special_tokens=False):return list(text.encode())
    def decode(self,ids,**kw):return bytes(ids).decode()

def snap(code='def f(x):\n    return x+1\n',**more):
    return dict(files={'a.py':code,**more},stable=True,limited=False)

class DenseContracts(unittest.TestCase):
    def session(self):return d.DynamicSession('function f returns an integer',Tok(),'task','session')
    def call(self,s,x,n):return s.capture(x,task_uid='task',session_id='session',logical_call_id=str(n),seq=n)
    def test_source_exact_and_budget(self):
        s=self.session();x=snap();r=self.call(s,x,0)
        self.assertLessEqual(len(r['pi_ids']),192);self.assertEqual(Tok().decode(r['pi_ids']),r['pi_text'])
        self.assertTrue(r['windows'])
        for w in r['windows']:
            self.assertEqual(w['code'],''.join(x['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
            self.assertEqual(w['source_hash'],d.sha(w['code']))
    def test_same_state_no_token_or_charge(self):
        s=self.session();self.call(s,snap(),0);left=s.remaining;r=self.call(s,snap(),1)
        self.assertEqual(r['pi_ids'],[]);self.assertEqual(left,s.remaining)
    def test_retry_is_exact_and_charged_once(self):
        s=self.session();a=self.call(s,snap(),0);left=s.remaining;b=self.call(s,snap(),0)
        self.assertEqual(a,b);self.assertEqual(left,s.remaining)
    def test_retry_changed_state_rejected(self):
        s=self.session();self.call(s,snap(),0)
        with self.assertRaisesRegex(ValueError,'retry'):self.call(s,snap('def f(x):\n    return x+2\n'),0)
    def test_cross_session_and_order_rejected(self):
        s=self.session();self.call(s,snap(),1)
        with self.assertRaises(ValueError):self.call(s,snap(),0)
        with self.assertRaisesRegex(ValueError,'cross-session'):s.capture(snap(),task_uid='other',session_id='session',logical_call_id='2',seq=2)
    def test_rollback_is_emitted(self):
        s=self.session();self.call(s,snap(),0)
        b=self.call(s,snap('def f(x):\n    return x+2\n'),1);a=self.call(s,snap(),2)
        self.assertTrue(b['pi_ids']);self.assertTrue(a['pi_ids']);self.assertNotEqual(b['state_hash'],a['state_hash'])
    def test_new_entity_enters_pool(self):
        s=self.session();self.call(s,snap(**{'b.py':'def g(x):\n    return x\n'}),0)
        r=self.call(s,snap(**{'b.py':'def g(x):\n    return x-3\n'}),1)
        self.assertIn('b.py',{w['file'] for w in r['windows']})
    def test_smallest_changed_method_not_whole_class(self):
        x=snap('class C:\n    def f(self):\n        return 1\n    def g(self):\n        return 2\n')
        y=snap(x['files']['a.py'].replace('return 2','return 3'))
        initial=d.build_initial_index(x,'class C',task_uid='t',session_id='s')['focus']
        selected=d.dynamic_candidates(initial,y,d.changes(x['files'],y['files']),'class C')
        self.assertEqual(selected[0]['qualified'],'C.g')
    def test_change_window_beats_strong_unchanged_issue(self):
        words='alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima'
        x=snap('def f():\n    return '+repr(words)+'\n',**{'b.py':'def g(x):\n    return x+1\n'})
        y=snap(x['files']['a.py'],**{'b.py':'def g(x):\n    return x-2\n'})
        initial=d.build_initial_index(x,words,task_uid='t',session_id='s')['focus']
        delta=d.changes(x['files'],y['files']);selected=d.dynamic_candidates(initial,y,delta,words)
        props=d.proposals(selected,y,words,delta)
        self.assertEqual(props[0]['file'],'b.py');self.assertGreater(props[0]['changed_lines'],0)
    def test_missing_status_explicit(self):
        s=self.session();self.call(s,snap(),0);x=dict(files={},stable=True,limited=False)
        r=self.call(s,x,1);self.assertIn('missing',r['pi_text']);self.assertTrue(r['unknown'])
    def test_limited_missing_not_proven_delete(self):
        facts=d.status_facts([],dict(files={},stable=True,limited=True),{'a.py':dict(kind='missing')})
        self.assertEqual(facts,[('a.py','','unobserved')])
    def test_invalid_source_is_failclosed(self):
        s=self.session()
        for x in [dict(files={'tests/test_x.py':'pass'},stable=True),dict(files={'../x.py':'pass'},stable=True),dict(files={},stable=False)]:
            with self.assertRaises(ValueError):self.call(s,x,0)
    def test_explicit_exhaustion_and_no_overspend(self):
        s=self.session();self.call(s,snap(),0);s.remaining=60
        r=self.call(s,snap('def f(x):\n    return x-5\n'),1)
        self.assertIn('exhausted',r['pi_text']);self.assertGreaterEqual(s.remaining,0)
        self.assertEqual(self.call(s,snap(),2)['pi_ids'],[])
    def test_parse_failure_visible(self):
        s=self.session();self.call(s,snap(),0);r=self.call(s,snap('def f(:\n    return 2\n'),1)
        self.assertTrue(r['unknown']);self.assertTrue('parse' in r['pi_text'] or 'unknown' in r['pi_text'])
    def test_inputs_not_mutated(self):
        x=snap();prior=copy.deepcopy(x);self.call(self.session(),x,0);self.assertEqual(x,prior)
    def test_deterministic_variants(self):
        x=snap();c=d.build_initial_index(x,'function f',task_uid='t',session_id='s')['focus']
        for variant in d.CONFIG['variants']:
            a=d.serialize(c,x,'function f',Tok(),variant=variant);b=d.serialize(c,x,'function f',Tok(),variant=variant)
            self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
