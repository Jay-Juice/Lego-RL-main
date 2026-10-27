import copy
import pathlib
import sys
import unittest
N=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'tests')]
import dense_state as d
from executable_windows import line_signals
from window_serializer import resolve
from test_dense_state import Tok, snap


class ExecutableContracts(unittest.TestCase):
    def fixture(self):
        code='def calculate(value):\n    """calculate calculate calculate"""\n    result = value + 1\n'
        code+='    sentinel = 0\n'*25
        code+='    return result\n'
        x=snap(code)
        c=d.build_initial_index(x,'calculate value result',task_uid='t',session_id='s')['focus']
        return x,c

    def test_docstrings_and_declarations_are_not_scoring_anchors(self):
        x,c=self.fixture();e=resolve(c,x['files'])[0]
        scores,excluded,_=line_signals(e,x['files']['a.py'].splitlines(True),'calculate value result')
        self.assertIn(1,excluded);self.assertIn(2,excluded)
        self.assertNotIn(1,scores);self.assertNotIn(2,scores)
        self.assertGreater(scores[3],0)

    def test_nonlocal_return_name_relation_is_bounded(self):
        x,c=self.fixture();e=resolve(c,x['files'])[0];lines=x['files']['a.py'].splitlines(True)
        body,_,_=line_signals(e,lines,'value',False)
        flow,_,linked=line_signals(e,lines,'value',True)
        self.assertIn(len(lines),linked)
        self.assertEqual(flow[len(lines)]-body[len(lines)],1)
        self.assertNotIn(4,linked)

    def test_exact_source_budget_and_immutable_inputs(self):
        x,c=self.fixture();original=copy.deepcopy((x,c))
        for variant in ('body_expand','flow_expand'):
            r=d.serialize(c,x,'calculate value result',Tok(),variant=variant)
            self.assertLessEqual(len(r['pi_ids']),192)
            self.assertEqual(Tok().decode(r['pi_ids']),r['pi_text'])
            for w in r['windows']:
                self.assertEqual(w['code'],''.join(x['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
        self.assertEqual((x,c),original)

    def test_changed_windows_still_first_for_new_variants(self):
        x,c=self.fixture();y=snap(x['files']['a.py'].replace('return result','return 0'))
        delta=d.changes(x['files'],y['files'])
        for variant in ('body_expand','flow_expand'):
            props=d.proposals(c,y,'calculate value result',delta,variant)
            self.assertGreater(props[0]['changed_lines'],0)

    def test_ast_parse_failure_does_not_invent_source(self):
        x,c=self.fixture();x['files']['a.py']='def calculate(:\n    return result\n'
        for variant in ('body_expand','flow_expand'):
            r=d.serialize(c,x,'calculate result',Tok(),variant=variant)
            for w in r['windows']:
                self.assertIn(w['code'],x['files']['a.py'])

if __name__=='__main__':unittest.main()
