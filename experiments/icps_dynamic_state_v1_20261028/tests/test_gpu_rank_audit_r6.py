"""Small CPU modules/synthetic rank rows. No distributed or GPU acceptance claims."""
import copy
import sys
import unittest
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from gpu_rank_audit_r6 import CRITIC_PATTERNS, parameter_audit, validate_rank_rows, compare_stages


def fixture(role='critic'):
    model = torch.nn.Module()
    for name in ('self_attn', 'linear_attn', 'visual', 'mlp', 'score' if role == 'critic' else 'lm_head'):
        model.add_module(name, torch.nn.Linear(2, 1 if name == 'score' else 2))
    if role == 'critic':
        for name, param in model.named_parameters():
            param.requires_grad_(not any(p in name for p in CRITIC_PATTERNS))
    optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=5e-6)
    return model, optim


def synthetic_rows(role, stage):
    model, optim = fixture(role)
    witness = parameter_audit(model, optim, CRITIC_PATTERNS if role == 'critic' else [], role)
    return [dict(copy.deepcopy(witness), role=role, stage=stage, rank=i, pid=100+i,
                 world_size=8, SP_size=8, DP_size=1, DP_rank=0, engine_class='SYNTHETIC',
                 module_MRO=['SYNTHETIC'], native_head_source={'SHA': 'SYNTHETIC'} if role == 'critic' else None)
            for i in range(8)]


class RankAuditTests(unittest.TestCase):
    def test_cpu_fixture_inspection_is_readonly(self):
        for role in ('actor', 'critic'):
            model, optim = fixture(role)
            before = {k: v.clone() for k, v in model.state_dict().items()}
            result = parameter_audit(model, optim, CRITIC_PATTERNS if role == 'critic' else [], role)
            self.assertGreater(result['trainable_tensors'], 0)
            self.assertFalse(optim.state)
            self.assertTrue(all(torch.equal(before[k], v) for k, v in model.state_dict().items()))

    def test_freeze_config_and_extra_freezing_rejected(self):
        model, optim = fixture()
        with self.assertRaises(RuntimeError):
            parameter_audit(model, optim, ['self_attn.'], 'critic')
        model.mlp.weight.requires_grad_(False)
        optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad])
        with self.assertRaises(RuntimeError):
            parameter_audit(model, optim, CRITIC_PATTERNS, 'critic')

    def test_unfrozen_attention_rejected(self):
        model, _ = fixture()
        model.self_attn.weight.requires_grad_(True)
        optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad])
        with self.assertRaises(RuntimeError):
            parameter_audit(model, optim, CRITIC_PATTERNS, 'critic')

    def test_optimizer_missing_extra_duplicate_rejected(self):
        for mode in ('missing', 'frozen', 'duplicate'):
            model, optim = fixture()
            params = optim.param_groups[0]['params']
            if mode == 'missing':
                params.pop()
            elif mode == 'frozen':
                params.append(model.visual.weight)
            else:
                params.append(params[0])
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                parameter_audit(model, optim, CRITIC_PATTERNS, 'critic')

    def test_nonscalar_or_lm_head_rejected(self):
        for mode in ('nonscalar', 'lm_head', 'missing'):
            model, _ = fixture()
            if mode == 'nonscalar':
                model.score = torch.nn.Linear(2, 2)
            elif mode == 'lm_head':
                model.lm_head = torch.nn.Linear(2, 2)
            else:
                del model.score
            optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad])
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                parameter_audit(model, optim, CRITIC_PATTERNS, 'critic')

    def test_unmatched_pattern_rejected(self):
        model, _ = fixture()
        del model.visual
        optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad])
        with self.assertRaises(RuntimeError):
            parameter_audit(model, optim, CRITIC_PATTERNS, 'critic')

    def test_synthetic_rank_coverage_topology_and_agreement(self):
        rows = synthetic_rows('critic', 'before')
        validate_rank_rows(rows, 'critic', 'before')
        with self.assertRaises(RuntimeError):
            validate_rank_rows(rows[:7], 'critic', 'before')
        for field, value in [('rank', 1), ('pid', 101), ('SP_size', 4), ('DP_size', 2),
                             ('role', 'actor'), ('stage', 'after'), ('parameter_inventory_SHA', 'changed'),
                             ('native_head_source', None), ('optimizer_tensors', 0)]:
            changed = copy.deepcopy(rows)
            changed[0][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate_rank_rows(changed, 'critic', 'before')

    def test_inventory_cannot_change_after_updates(self):
        before = {role: synthetic_rows(role, 'before') for role in ('actor', 'critic')}
        after = {role: synthetic_rows(role, 'after') for role in ('actor', 'critic')}
        compare_stages(before, after)
        after['critic'][3]['parameter_inventory_SHA'] = 'changed'
        with self.assertRaises(RuntimeError):
            compare_stages(before, after)

    def test_native_worker_subclasses_only_add_audit(self):
        from gpu_probe_workers_r6 import AuditedActorWorker, AuditedCriticWorker
        from verl.workers.engine_workers import ActorRolloutRefWorker, TrainingWorker
        from verl.single_controller.base.decorator import Dispatch, MAGIC_ATTR
        for cls, base, names in [(AuditedActorWorker, ActorRolloutRefWorker, ['init_model', 'update_actor']),
                                 (AuditedCriticWorker, TrainingWorker, ['reset', 'train_mini_batch', 'infer_batch'])]:
            self.assertEqual(cls.__bases__, (base,))
            for name in names:
                self.assertIs(getattr(cls, name), getattr(base, name))
            attrs = getattr(cls.r6_rank_audit, MAGIC_ATTR)
            self.assertEqual(attrs['dispatch_mode'], Dispatch.ONE_TO_ALL)
            self.assertTrue(attrs['blocking'])
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__':
    unittest.main(verbosity=2)
