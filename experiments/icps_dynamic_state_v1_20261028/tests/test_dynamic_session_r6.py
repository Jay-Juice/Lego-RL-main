import ast, inspect, pathlib, sys, unittest
N=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
import dense_state as d
from dynamic_session_r6 import R6DynamicSession, serialize_state
from rank_windows_r6 import serialize as initial_serialize
import test_dense_state as base

class SessionContracts(base.DenseContracts):
    def session(self):
        return R6DynamicSession('function f returns an integer',base.Tok(),'task','session')

    def test_capture_transition_AST_unchanged(self):
        a=ast.parse(inspect.getsource(d.DynamicSession))
        b=ast.parse(inspect.getsource(R6DynamicSession))
        ac=next(x for x in a.body[0].body if isinstance(x,ast.FunctionDef) and x.name=='capture')
        bc=next(x for x in b.body[0].body if isinstance(x,ast.FunctionDef) and x.name=='capture')
        for x in ast.walk(bc):
            if isinstance(x,ast.Name) and x.id=='serialize_state':x.id='serialize'
        self.assertEqual(ast.dump(ac),ast.dump(bc))

    def test_W0_exact_frozen_payload(self):
        s=self.session();x=base.snap();z=self.call(s,x,0)
        expected=initial_serialize(s.initial,x,s.issue,s.tokenizer,variant='novelty_cost_expand')
        self.assertEqual({k:z[k] for k in expected},expected)

    def test_status_path_and_updates_exact_R4(self):
        x=base.snap();t=base.Tok();c=d.build_initial_index(x,'function f',task_uid='t',session_id='s')['focus']
        for status,facts,delta in [('initial',[('a.py','f','unknown')],{}),('current_change',[],{'a.py':{'ranges':[(2,2)]}})]:
            args=dict(budget=128,delta=delta,variant='flow_expand',facts=facts,status=status)
            self.assertEqual(serialize_state(c,x,'function f',t,**args),d.serialize(c,x,'function f',t,**args))

    def test_update_variant_cannot_drift(self):
        with self.assertRaises(ValueError):R6DynamicSession('',base.Tok(),'t','s',variant='compact')

    def test_natural_exhaustion(self):
        s=self.session();charged=0
        for i in range(150):
            z=self.call(s,base.snap('def f(x):\n    return x+'+str(i)+'\n'),i)
            charged+=len(z['pi_ids'])
            self.assertEqual(charged+s.remaining,4096)
            self.assertLessEqual(len(z['pi_ids']),192 if i==0 else 128)
            if s.exhausted:break
        self.assertTrue(s.exhausted);self.assertIn('exhausted',z['pi_text'])
        self.assertGreaterEqual(s.remaining,0)

if __name__=='__main__': unittest.main()
