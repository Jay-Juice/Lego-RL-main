"""Control-flow and real native per-batch packing contract, no GPU required."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

F=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(F/'src'))
from formal_packing import budget

def method(source,name):
    tree=ast.parse(source)
    return next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)

class Full97(unittest.TestCase):
    def test_all97_budgets(self):
        for step in range(1,98):
            self.assertEqual(budget('actor_train',step),14336 if step<=20 else 16384)
            self.assertEqual(budget('critic_infer',step),32768)
            for role in ['critic_train']:
                self.assertEqual(budget(role,step),20480 if step<=20 else 45056)

    def test_no_invalid_phase(self):
        for step in [0,98,None,True,20.0]:
            with self.assertRaises(ValueError):budget('actor_train',step)
        with self.assertRaises(ValueError):budget('actor_logprob',21)

    def test_real_fit_stop_control_unchanged_from_passed_v11(self):
        # Compare actual branching/return/save/step control to the frozen passed
        # online v1.1 trainer, removing only the entry witness statement pair.
        old=F.parents[1]/'diagnostics/icps_v11_window_20261023/runtime_candidate_r3/ray_trainer.py'
        if not old.exists():
            old=Path('/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015/ops/icps_v11_window_20261023/runtime_candidate_r3/ray_trainer.py')
        orig=method(old.read_text(encoding='utf-8'),'fit')
        new=method((F/'runtime/ray_trainer.py').read_text(encoding='utf-8'),'fit')
        class Strip(ast.NodeTransformer):
            def visit_ImportFrom(self,n):return None if n.module=='formal_packing' else n
            def visit_Expr(self,n):
                return None if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='record_phase' else n
        self.assertEqual(ast.dump(orig,include_attributes=False),ast.dump(Strip().visit(new),include_attributes=False))

    def test_all_actual_fit_returns_are_native(self):
        fit=method((F/'runtime/ray_trainer.py').read_text(encoding='utf-8'),'fit')
        self.assertEqual(sum(isinstance(n,ast.Return) for n in ast.walk(fit)),2)
        text=ast.unparse(fit)
        self.assertIn('if is_last_step:',text)
        self.assertIn('self.global_steps >= self.total_training_steps',text)
        self.assertIn('self.global_steps += 1',text)
        self.assertNotIn('formal_pause',text)

    def test_no_active_pause_or_shortened_horizon(self):
        for path in [F/'ICPS_V11_FULL_LAUNCH_CONFIG.env',F/'src/formal_main.py',F/'runtime/ray_trainer.py']:
            text=path.read_text(encoding='utf-8')
            for word in ['ICPS_PAUSE_AFTER_COMPLETED_STEP','PAUSED_AT_STEP20','pause_after_completed_step','total_training_steps=20']:
                self.assertNotIn(word,text)
        self.assertFalse((F/'src/formal_pause.py').exists())

    def test_save_native_unchanged(self):
        actual=(F/'runtime/ray_trainer.py').read_text(encoding='utf-8')
        original=(F/'runtime/original/ray_trainer.py').read_text(encoding='utf-8')
        self.assertEqual(ast.dump(method(actual,'_save_checkpoint')),ast.dump(method(original,'_save_checkpoint')))

    def test_phase21_only_engineering_overrides(self):
        actual=(F/'runtime/ray_trainer.py').read_text(encoding='utf-8')
        for name,role in [('_update_actor','actor_train'),('_update_critic','critic_train')]:
            code=ast.unparse(method(actual,name))
            self.assertIn(f"budget('{role}', self.global_steps)",code)
            self.assertNotIn('scheduler',code)
            self.assertNotIn('optimizer',code)
        for name in ['_compute_values','_compute_old_log_prob','_compute_ref_log_prob']:
            self.assertNotIn('budget(',ast.unparse(method(actual,name)))

    def test_all_eight_ranks_honor_native_override(self):
        p=Path('/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015/third_party/verl/verl/workers/engine_workers.py')
        if not p.exists():p=F.parents[0]/'pi_repair_state_v2_20261015/third_party/verl/verl/workers/engine_workers.py'
        native=p.read_text(encoding='utf-8')
        # Execute the exact defaults-injection loop from native train/infer on
        # fake ranks; no reimplementation of that conditional is used.
        loops=[]
        for name in ['train_batch','infer_batch']:
            func=method(native,name)
            loops.append(next(n for n in func.body if isinstance(n,ast.For) and 'default_keys.items' in ast.unparse(n)))
        class TU:
            @staticmethod
            def assign_non_tensor(data,**kwargs):data.update(kwargs)
        for step in [1,19,20,21,50,97]:
            for rank in range(8):
                for role,loop in [('actor_train',loops[0]),('critic_train',loops[0]),('critic_infer',loops[1])]:
                    data={'max_token_len_per_gpu':budget(role,step),'input_ids':'unaltered','loss_mask':'unaltered'}
                    scope=dict(data=data,default_keys={'max_token_len_per_gpu':123,'use_dynamic_bsz':True},tu=TU)
                    exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(loop)],type_ignores=[])),'native_defaults','exec'),scope)
                    self.assertEqual(data['max_token_len_per_gpu'],budget(role,step))
                    self.assertEqual(data['input_ids'],'unaltered');self.assertEqual(data['loss_mask'],'unaltered')

    def test_old_copy_and_backup_unchanged(self):
        proof=json.loads((F/'preflight/NEW_COPY_PROVENANCE.json').read_text())
        old=Path(proof['source'])
        # On Linux, Windows authoritative proof cannot be checked directly.
        if old.exists():
            for name,digest in proof['source_hashes'].items():
                self.assertEqual(hashlib.sha256((old/name).read_bytes()).hexdigest(),digest)
            self.assertEqual(hashlib.sha256(Path(proof['backup']).read_bytes()).hexdigest(),proof['backup_sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
