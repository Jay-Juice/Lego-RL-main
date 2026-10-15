import copy
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from harbor_patch.privileged_state.container_capture import collect
from harbor_patch.privileged_state import container_capture
from harbor_patch.privileged_state.structural_lift import build_snapshot, lift, serialize
from verl_patch.agent_loop.privileged_critic_builder import interleave, remap_rebuilt_records


def record(start, end, state, ids):
    return {"actor_response_start_abs": start, "actor_response_end_abs": end,
            "state_hash": state, "pi_ids": ids, "valid": True}


def item(current, old="", path="f.py", status="modified"):
    return {"path": path, "current_source": current, "old_source": old, "status": status, "kind": "text"}


class StructuralTests(unittest.TestCase):
    def test_real_file_change_between_stat_and_read_recaptures_current_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            target = root / "live.txt"
            target.write_text("prepared\n")
            subprocess.run(["git", "-C", directory, "add", "-A"], check=True)
            subprocess.run(["git", "-C", directory, "-c", "user.name=test", "-c", "user.email=t@local",
                            "commit", "-qm", "base"], check=True)
            baseline = collect(directory)["baseline_sha"]
            target.write_text("earlier state\n")
            original_open = pathlib.Path.open
            changed = False

            def racing_open(path, mode="r", *args, **kwargs):
                nonlocal changed
                if path == target and mode == "rb" and not changed:
                    changed = True
                    with original_open(target, "w") as writer:
                        writer.write("latest current state after concurrent write\n")
                return original_open(path, mode, *args, **kwargs)

            with patch.object(pathlib.Path, "open", racing_open), patch.object(container_capture.time, "sleep"):
                snapshot = collect(directory, baseline)
            self.assertTrue(changed)
            self.assertEqual(snapshot["baseline_sha"], baseline)
            self.assertEqual(snapshot["capture_attempts"], 2)
            self.assertEqual(snapshot["files"][0]["current_source"], "latest current state after concurrent write\n")
            self.assertEqual(snapshot["files"][0]["old_source"], "prepared\n")

    def test_snapshot_retry_discards_partial_files_and_keeps_fixed_baseline(self):
        partial = {"files": [{"path": "partial.py"}]}
        final = {"files": [{"path": "current.py"}], "captured_at_start_ns": 1}
        calls = []

        def once(root, baseline):
            calls.append((root, baseline))
            if len(calls) == 1:
                partial["files"].append({"path": "mixed.py"})
                raise container_capture.UnstableSnapshotError("File changed during PI capture: f.py")
            return copy.deepcopy(final)

        with patch.object(container_capture, "_collect_once", side_effect=once), \
             patch.object(container_capture.time, "sleep"):
            snapshot = collect("/current/worktree", "fixed-buggy-sha")
        self.assertEqual(calls, [("/current/worktree", "fixed-buggy-sha")] * 2)
        self.assertEqual(snapshot["files"], final["files"])
        self.assertEqual(snapshot["capture_attempts"], 2)
        self.assertEqual(len(snapshot["capture_retry_errors"]), 1)

    def test_snapshot_retry_exhaustion_and_non_transient_errors(self):
        for error in [container_capture.UnstableSnapshotError("inventory changed"), FileNotFoundError("gone")]:
            with self.subTest(error=type(error).__name__), \
                 patch.object(container_capture, "_collect_once", side_effect=error) as once, \
                 patch.object(container_capture.time, "sleep") as delay:
                with self.assertRaisesRegex(container_capture.UnstableSnapshotError, "after 5 attempts"):
                    collect("/worktree", "fixed-sha")
                self.assertEqual(once.call_count, 5)
                self.assertEqual(delay.call_count, 4)
        for baseline in [None, "fixed-sha"]:
            with self.subTest(baseline=baseline), \
                 patch.object(container_capture, "_collect_once", side_effect=RuntimeError("byte budget exceeded")) as once:
                with self.assertRaisesRegex(RuntimeError, "byte budget exceeded"):
                    collect("/worktree", baseline)
                self.assertEqual(once.call_count, 1)

    def test_cumulative_delta_commit_restore_and_untracked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            f = root / "f.py"
            a = "def f(x):\n    return x + 1\n"
            f.write_text(a)
            (root / ".gitignore").write_text("ignored.py\n")
            subprocess.run(["git", "-C", directory, "add", "-A"], check=True)
            subprocess.run(["git", "-C", directory, "-c", "user.name=test", "-c", "user.email=t@local",
                            "commit", "-qm", "base"], check=True)
            baseline = collect(directory)
            initial = build_snapshot(collect(directory, baseline["baseline_sha"]))
            f.write_text(a.replace("+ 1", "+ 2"))
            edited = build_snapshot(collect(directory, baseline["baseline_sha"]))
            self.assertNotEqual(initial["state_hash"], edited["state_hash"])
            self.assertIn("return x + 2", edited["entities"][0]["current_source"])
            subprocess.run(["git", "-C", directory, "add", "f.py"], check=True)
            subprocess.run(["git", "-C", directory, "-c", "user.name=test", "-c", "user.email=t@local",
                            "commit", "-qm", "actor_commit"], check=True)
            self.assertEqual(edited["state_hash"], build_snapshot(collect(directory, baseline["baseline_sha"]))["state_hash"])
            f.write_text(a)
            self.assertEqual(initial["state_hash"], build_snapshot(collect(directory, baseline["baseline_sha"]))["state_hash"])
            (root / "new.py").write_text("async def g():\n    return 7\n")
            (root / "ignored.py").write_text("secret = 9")
            added = build_snapshot(collect(directory, baseline["baseline_sha"]))
            self.assertEqual(added["changed_files"], ["new.py"])
            self.assertEqual(added["entities"][0]["kind"], "async_function")
            f.unlink()
            removed = build_snapshot(collect(directory, baseline["baseline_sha"]))
            self.assertTrue(any(e["status"] == "removed" and e["qualname"] == "f" for e in removed["entities"]))

    def test_method_class_nested_and_decorator(self):
        old = "class C:\n    n = 1\n    @staticmethod\n    def f():\n        def g():\n            return 1\n        return g()\n"
        new = old.replace("return 1", "return 2")
        entities, failed = lift(item(new, old))
        self.assertEqual(failed, 0)
        self.assertEqual(entities[0]["qualname"], "C.f.g")
        entities, _ = lift(item(old.replace("return g()", "return 3"), old))
        self.assertEqual(entities[0]["qualname"], "C.f")
        self.assertTrue(entities[0]["current_source"].startswith("    @staticmethod"))
        entities, _ = lift(item(old.replace("n = 1", "n = 2"), old))
        self.assertEqual(entities[0]["kind"], "class")

    def test_module_syntax_and_removed_scope(self):
        old = "import os\n\ndef f():\n    return 1\n"
        entities, _ = lift(item(old.replace("import os", "import sys"), old))
        self.assertEqual(entities[0]["kind"], "module_region")
        entities, failed = lift(item("def f(:\n    return 1", old))
        self.assertEqual(failed, 1)
        self.assertTrue(any(e.get("parse_status") == "syntax_error" for e in entities))
        entities, _ = lift(item("import os\n", old))
        self.assertTrue(any(e["status"] == "removed" and e["current_source"] is None for e in entities))

    def test_hard_token_budget(self):
        class CharTokenizer:
            def encode(self, text, **kwargs): return list(map(ord, text))
            def decode(self, ids, **kwargs): return "".join(map(chr, ids))
        snapshot = {"changed_files": ["f.py"], "parse_failure_count": 0,
                    "entities": [{"current_source": "x" * 3000}]}
        text, ids, raw_count, truncated = serialize(snapshot, CharTokenizer(), 300)
        self.assertTrue(truncated)
        self.assertGreater(raw_count, len(ids))
        self.assertLessEqual(len(ids), 300)
        self.assertIn("truncated: true", text)
        self.assertTrue(text.endswith("[/PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\n"))


class MappingTests(unittest.TestCase):
    def test_pre_action_mapping_dedup_restore_and_truncation(self):
        actor = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        mask = [1, 1, 0, 1, 0, 1, 1]
        recs = [record(2, 4, "A", [21, 22]), record(5, 6, "A", [21, 22]), record(7, 9, "B", [23])]
        saved = copy.deepcopy((actor, mask, recs))
        ids, gather, p_mask = interleave(actor, 2, mask, recs)
        self.assertEqual(ids, [1, 2, 21, 22, 3, 4, 5, 6, 7, 23, 8, 9])
        self.assertEqual(gather, [3, 4, 5, 6, 7, 9, 10])
        self.assertEqual(sum(p_mask), 3)
        self.assertEqual((actor, mask, recs), saved)
        recs[-1]["pi_ids"] = [30, 31, 32]
        changed, changed_gather, _ = interleave(actor, 2, mask, recs)
        self.assertEqual(ids[:gather[3] + 1], changed[:changed_gather[3] + 1])
        truncated_ids, _, _ = interleave(actor[:7], 2, mask[:5], recs)
        self.assertNotIn(30, truncated_ids)
        recs[-1] = record(7, 9, "A", [21, 22])
        self.assertEqual(sum(interleave(actor, 2, mask, recs)[2]), 2)

    def test_empty_pi_and_missing_capture(self):
        ids, gather, _ = interleave([1, 2, 3, 4], 2, [1, 1], [record(2, 4, "A", [])])
        self.assertEqual(ids, [1, 2, 3, 4])
        self.assertEqual(gather, [1, 2])
        with self.assertRaises(ValueError): interleave([1, 2, 3], 1, [1, 1], [])

    def test_rewrite_join_and_unknown_history(self):
        recs = [{**record(2, 4, "A", [21]), "message_key": "first"},
                {**record(6, 8, "B", [22]), "message_key": "second"}]
        rebuilt = remap_rebuilt_records(recs, [("second", 5, 9)])
        self.assertEqual(rebuilt[0]["state_hash"], "B")
        self.assertEqual(rebuilt[0]["actor_response_start_abs"], 5)
        with self.assertRaises(RuntimeError): remap_rebuilt_records(recs, [("unknown", 2, 4)])


class TensorTests(unittest.TestCase):
    def setUp(self):
        import torch
        torch.set_num_threads(2)

    def batch(self, pi=True, empty=False):
        import numpy as np
        import torch
        from verl import DataProto
        data = {"input_ids": torch.tensor([[0, 1, 2, 3, 4, 5, 0], [0, 0, 6, 7, 8, 0, 0]]),
                "attention_mask": torch.tensor([[0, 1, 1, 1, 1, 1, 0], [0, 0, 1, 1, 1, 0, 0]]),
                "prompts": torch.tensor([[0, 1, 2], [0, 0, 6]]),
                "responses": torch.tensor([[3, 4, 5, 0], [7, 8, 0, 0]]),
                "response_mask": torch.tensor([[1, 0, 1, 0], [0, 0, 0, 0]]),
                "position_ids": torch.tensor([[0, 0, 1, 2, 3, 4, 0], [0, 0, 0, 1, 2, 0, 0]]),
                "values": torch.zeros(2, 4), "returns": torch.tensor([[1., 0., 1., 0.], [0., 0., 0., 0.]])}
        non_tensor = {}
        if pi:
            array = np.empty(2, dtype=object)
            array[:] = [[record(2, 3, "A", [] if empty else [21]), record(4, 5, "B", [] if empty else [22])], []]
            non_tensor["pi_call_records"] = array
        return DataProto.from_dict(data, non_tensor)

    def test_tensor_view_actor_unchanged_and_gradient(self):
        import torch
        from verl_patch.agent_loop.privileged_critic_builder import prepare_critic_view
        from verl.workers.utils.padding import no_padding_2_padding
        batch = self.batch()
        saved = {k: v.clone() for k, v in batch.batch.items()}
        data = prepare_critic_view(batch.to_tensordict())
        for k, v in saved.items(): torch.testing.assert_close(v, batch.batch[k], rtol=0, atol=0)
        values = torch.arange(int(data["input_ids"].offsets()[-1]), dtype=torch.float32, requires_grad=True)
        gathered = no_padding_2_padding(values, data)
        self.assertEqual(gathered.shape, (2, 4))
        self.assertEqual(gathered[0].tolist(), [2., 3., 5., 0.])
        gathered.sum().backward()
        self.assertEqual(values.grad[2], 1)
        self.assertEqual(values.grad[5], 1)
        from verl.utils import tensordict_utils as tu
        for i in range(2):
            subset = tu.index_select_tensor_dict(data, [i])
            local = values[data["input_ids"].offsets()[i]:data["input_ids"].offsets()[i+1]]
            torch.testing.assert_close(no_padding_2_padding(local, subset), gathered[i:i+1])

    def test_real_tiny_value_model_empty_equivalence_loss_gradient_and_future(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForTokenClassification
        from verl.workers.config import CriticConfig
        from verl.utils import tensordict_utils as tu
        from verl.workers.utils.losses import value_loss
        from verl.workers.utils.padding import no_padding_2_padding
        from verl_patch.agent_loop.privileged_critic_builder import prepare_critic_view
        torch.manual_seed(42)
        config = Qwen3Config(vocab_size=64, hidden_size=32, intermediate_size=48, num_hidden_layers=2,
                             num_attention_heads=2, num_key_value_heads=2, head_dim=16, num_labels=1,
                             attention_dropout=0, classifier_dropout=0, pad_token_id=0)
        config._attn_implementation = "eager"
        model = Qwen3ForTokenClassification(config).eval()
        critic_cfg = CriticConfig(strategy="veomni", ppo_mini_batch_size=2, ppo_micro_batch_size_per_gpu=1)
        outputs, losses, grads = [], [], []
        for pi in (False, True):
            model.zero_grad()
            data = prepare_critic_view(self.batch(pi=pi, empty=True).to_tensordict())
            values = torch.cat([model(input_ids=ids[None]).logits[0, :, 0] for ids in data["input_ids"].unbind()])
            tu.assign_non_tensor(data, dp_size=1, batch_num_tokens=2, global_batch_size=2)
            loss, _ = value_loss(critic_cfg, {"values": values}, data)
            outputs.append(no_padding_2_padding(values, data).detach())
            loss.backward()
            losses.append(loss.detach())
            grads.append({k: p.grad.clone() for k, p in model.named_parameters() if p.grad is not None})
        torch.testing.assert_close(outputs[0], outputs[1], rtol=0, atol=0)
        torch.testing.assert_close(losses[0], losses[1], rtol=0, atol=0)
        for k in grads[0]: torch.testing.assert_close(grads[0][k], grads[1][k], rtol=0, atol=0)
        from verl.trainer.ppo.core_algos import compute_gae_advantage_return
        rewards = torch.tensor([[0., 0., 1., 0.], [0., 0., 0., 0.]])
        mask = self.batch().batch["response_mask"]
        # Same SAO skip-observation GAE, including critic lambda and whitening.
        gae = [compute_gae_advantage_return(rewards, output, mask, 1., 0.9, 1., True) for output in outputs]
        for a, b in zip(gae[0], gae[1], strict=True):
            torch.testing.assert_close(a, b, rtol=0, atol=0)
        data = prepare_critic_view(self.batch().to_tensordict())
        ids = data["input_ids"].unbind()[0].clone()
        before = model(input_ids=ids[None]).logits[0, :, 0]
        ids[-2] = 30  # PI for the later call; cannot affect earlier values.
        after = model(input_ids=ids[None]).logits[0, :, 0]
        torch.testing.assert_close(before[:3], after[:3], rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
