import ast, inspect, unittest
import test_dynamic_session_r6 as original
import test_dense_state as base
import dense_state as d
from dynamic_session_r6_r2 import R6DynamicSessionR2

class BoundaryContracts(original.SessionContracts):
    def session(self):
        return R6DynamicSessionR2('function f returns an integer',base.Tok(),'task','session')

    def test_capture_transition_AST_unchanged(self):
        # The only lifecycle changes are serializer dispatch and the normalized
        # internal key. The public frozen W0 semantic field is not rewritten.
        a=ast.parse(inspect.getsource(d.DynamicSession))
        s=inspect.getsource(R6DynamicSessionR2)
        s=s.replace('                visible=session_semantic(out,snapshot,first,facts)\n','')
        s=s.replace('if visible==self.last_visible',"if out['semantic_hash']==self.last_visible")
        s=s.replace('else:self.last_visible=visible',"else:self.last_visible=out['semantic_hash']")
        s=s.replace('out=serialize_state(', 'out=serialize(')
        b=ast.parse(s)
        def capture(x):return next(f for f in x.body[0].body if isinstance(f,ast.FunctionDef) and f.name=='capture')
        self.assertEqual(ast.dump(capture(a)),ast.dump(capture(b)))

    def test_initial_update_same_visible_source_does_not_charge(self):
        s=self.session()
        x=base.snap(**{'b.py':'# unchanged\n'})
        y=base.snap(**{'b.py':'# unrelated changed comment\n'})
        initial=self.call(s,x,0);left=s.remaining
        update=self.call(s,y,1)
        self.assertTrue(initial['windows'])
        self.assertEqual(update['pi_ids'],[])
        self.assertEqual(left,s.remaining)
        self.assertEqual(initial['state_hash'],update['state_hash'])

if __name__=='__main__':unittest.main()
