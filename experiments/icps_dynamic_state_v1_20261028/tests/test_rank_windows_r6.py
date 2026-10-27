import pathlib,sys,unittest
N=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
from issue_program_state import build_initial_index
from rank_windows_r6 import serialize,marginal_score
from test_dense_state import Tok

class RankContracts(unittest.TestCase):
    def test_repeated_query_reduces_only_marginal_utility(self):
        self.assertEqual(marginal_score(4,{'a','b'},set(),9,'novelty_expand'),4)
        self.assertAlmostEqual(marginal_score(4,{'a','b'},{'a'},9,'novelty_expand'),4/1.5)
        self.assertEqual(marginal_score(4,{'a','b'},{'a','b'},9,'novelty_expand'),2)
        self.assertAlmostEqual(marginal_score(4,{'a','b'},set(),9,'novelty_cost_expand'),4/3)
    def test_actual_source_budget_and_no_overlap(self):
        for count in [2,5,15,40]:
            for budget in [128,192]:
                s=dict(stable=True,limited=False,files={'a.py':'def f(x):\n'+''.join('    x += '+str(i)+'\n' for i in range(count))+'    return x\n','b.py':'def g(x):\n    return x-1\n'})
                c=build_initial_index(s,'function f returns wrong x',task_uid='t',session_id='s')['focus']
                for v in ['novelty_expand','novelty_cost_expand']:
                    z=serialize(c,s,'function f returns wrong x',Tok(),budget=budget,variant=v)
                    self.assertLessEqual(len(z['pi_ids']),budget);self.assertLessEqual(len(z['windows']),3)
                    self.assertEqual(Tok().decode(z['pi_ids']),z['pi_text']);seen=set()
                    for w in z['windows']:
                        self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
                        points={(w['file'],i) for i in range(w['start'],w['end']+1)}
                        self.assertFalse(points&seen);seen|=points
    def test_bad_inputs_failclosed(self):
        with self.assertRaises(ValueError):serialize([],dict(stable=False,files={}),'',Tok())
        with self.assertRaises(ValueError):serialize([],dict(stable=True,files={}),'',Tok(),variant='oracle')

if __name__=='__main__':unittest.main()
