"""Actual offline tokenizer, two new selectors, no weights/optimizer."""
import json
import pathlib
import sys
import unittest
N=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(N/'tests'))
import test_dense_real as real
import test_executable_windows as executable
executable.Tok=lambda:real.tok

suite=unittest.TestSuite()
for variant in ('body_expand','flow_expand'):
    def session(self,variant=variant):
        return real.base.d.DynamicSession('function f returns an integer',real.tok,'task','session',variant=variant)
    case=type('Real_'+variant,(real.RealContracts,),{'session':session})
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(executable.ExecutableContracts))
result=unittest.TextTestRunner(verbosity=2).run(suite)
receipt=dict(tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
    variants=['body_expand','flow_expand'],tokenizer='local Qwen3.5-9B',GPU_jobs=0,optimizer_steps=0)
with (N/'reports/REAL_TOKENIZER_CONTRACTS_r4.json').open('x') as f:json.dump(receipt,f,indent=2)
sys.exit(0 if result.wasSuccessful() else 1)
