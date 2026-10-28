"""Negative config-boundary tests; no Ray/model imports or launch receipts."""
import copy
import json
from pathlib import Path
import sys
import unittest

N_LOCAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(N_LOCAL/'src'))
from gpu_launch_config_r6 import bind_private_config, validate_private_config, differences, N
from gpu_launch_gate_r6 import GateError


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.seed = json.loads((N_LOCAL/'reports/GPU_PROBE_R6_HYDRA_PARITY.json').read_text())['complete_actual_config']
        self.run = N/'runs/gpu-r6-1122334455667788'
        self.value = bind_private_config(self.seed, self.run)

    def test_exact_transform_seed_unmodified(self):
        old = copy.deepcopy(self.seed)
        self.assertEqual(len(validate_private_config(self.value, self.seed, self.run)), 7)
        self.assertEqual(self.seed, old)
        self.assertEqual(self.value['critic'], self.seed['critic'])
        self.assertEqual(self.value['actor_rollout_ref'], self.seed['actor_rollout_ref'])

    def test_training_changes_rejected(self):
        changes = [('trainer.resume_mode', 'auto'), ('trainer.total_epochs', 2),
            ('critic.optim.lr', 1e-6), ('critic.ppo_epochs', 1),
            ('critic.veomni.freeze_param_patterns', []),
            ('critic.checkpoint.save_contents', ['model']),
            ('actor_rollout_ref.actor.ppo_max_token_len_per_gpu', 16384),
            ('algorithm.gamma', 0.99), ('data.train_batch_size', 1)]
        for path, value in changes:
            changed = copy.deepcopy(self.value)
            target = changed
            parts = path.split('.')
            for key in parts[:-1]:
                target = target[key]
            target[parts[-1]] = value
            with self.subTest(path=path), self.assertRaises(GateError):
                validate_private_config(changed, self.seed, self.run)

    def test_ray_and_unknown_keys_rejected(self):
        for key, value in [('address', 'auto'), ('_temp_dir', '/tmp/ray'),
                           ('num_gpus', True), ('namespace', 'shared'),
                           ('include_dashboard', True), ('ignore_reinit_error', True)]:
            changed = copy.deepcopy(self.value)
            changed['ray_kwargs']['ray_init'][key] = value
            with self.subTest(key=key), self.assertRaises(GateError):
                validate_private_config(changed, self.seed, self.run)

    def test_wrong_run_and_output_binding(self):
        other = N/'runs/gpu-r6-8877665544332211'
        with self.assertRaises(GateError):
            validate_private_config(self.value, self.seed, other)
        for run in [N/'runs/old', N/'runs/gpu-r6-1122334455667788/../other',
                    Path('/tmp/gpu-r6-1122334455667788')]:
            with self.subTest(run=run), self.assertRaises(GateError):
                bind_private_config(self.seed, run)

    def test_missing_null_and_bool_integer_distinguished(self):
        self.assertTrue(differences({}, {'x': None}))
        self.assertTrue(differences({'x': True}, {'x': 1}))
        changed = copy.deepcopy(self.value)
        del changed['trainer']['resume_from_path']
        with self.assertRaises(GateError):
            validate_private_config(changed, self.seed, self.run)


if __name__ == '__main__':
    unittest.main(verbosity=2)
