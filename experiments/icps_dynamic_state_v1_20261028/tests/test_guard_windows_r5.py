import pathlib,sys,unittest
N=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
from issue_program_state import build_initial_index
from window_serializer import serialize as original
from guard_windows_r5 import serialize
from test_dense_state import Tok

def lines(z): return {(m['file'],p['line']) for m in z['source_map'] for p in m['pi_emitted_source_spans_W0']}

class GuardContracts(unittest.TestCase):
    def test_current_source_preservation_and_budget(self):
        for count in [2,5,15,40]:
            for budget in [128,192]:
                s=dict(stable=True,limited=False,files={'a.py':'def f(x):\n'+''.join('    x += '+str(i)+'\n' for i in range(count))+'    return x\n','b.py':'def g(x):\n    return x-1\n'})
                c=build_initial_index(s,'function f returns wrong x',task_uid='t',session_id='s')['focus']
                old=original(c,s,'function f returns wrong x',Tok(),budget=budget)
                for variant in ['guard_expand','anchor_expand']:
                    new=serialize(c,s,'function f returns wrong x',Tok(),budget=budget,variant=variant)
                    self.assertLessEqual(len(new['pi_ids']),budget);self.assertLessEqual(len(new['windows']),3)
                    self.assertEqual(Tok().decode(new['pi_ids']),new['pi_text'])
                    if variant=='guard_expand': self.assertTrue(lines(old)<=lines(new))
                    for w in new['windows']: self.assertEqual(w['code'],''.join(s['files'][w['file']].splitlines(True)[w['start']-1:w['end']]))
    def test_unstable_failclosed(self):
        with self.assertRaises(ValueError):serialize([],dict(stable=False,files={}),'',Tok())
    def test_unknown_variant_rejected(self):
        with self.assertRaises(ValueError):serialize([],dict(stable=True,files={}),'',Tok(),variant='oracle')

if __name__=='__main__':unittest.main()
