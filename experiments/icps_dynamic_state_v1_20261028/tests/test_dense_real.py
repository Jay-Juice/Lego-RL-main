"""Offline real-Qwen tokenizer contracts. No model or optimizer is loaded."""
import json,os,pathlib,sys,unittest
N=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(N/'tests'))
import test_dense_state as base
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('/media/ubuntu/D1/zsj/Lego-RL-main/Qwen3.5-9B',local_files_only=True)
base.Tok=lambda:tok
class RealContracts(base.DenseContracts):
    def test_explicit_exhaustion_and_no_overspend(self):
        s=self.session();self.call(s,base.snap(),0);total=4096-s.remaining;exhausted=False
        for i in range(1,350):
            r=self.call(s,base.snap(f'def f(x):\n    return x+{i}\n'),i)
            self.assertLessEqual(len(r['pi_ids']),128)
            self.assertEqual(tok.decode(r['pi_ids'],skip_special_tokens=False),r['pi_text'])
            total+=len(r['pi_ids']);self.assertLessEqual(total,4096)
            if 'exhausted' in r['pi_text']:
                exhausted=True
                self.assertEqual(self.call(s,base.snap(),i+1)['pi_ids'],[])
                break
        self.assertTrue(exhausted);self.assertEqual(s.remaining,4096-total)
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RealContracts))
    receipt=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),tokenizer='local Qwen3.5-9B',GPU_jobs=0,optimizer_steps=0)
    out=N/'reports/REAL_TOKENIZER_CONTRACTS.json'
    with out.open('x') as f:json.dump(receipt,f,indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
