"""Isolated eight-GPU real-engine smoke on a synthetic short batch; no checkpoints."""
import json
import math
import os
from pathlib import Path

import hydra
import numpy as np
import ray
import torch
from verl import DataProto
from verl.trainer.main_ppo import TaskRunner, run_ppo
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from verl.utils.metric import reduce_metrics


def short_batch(tokenizer, pi=True, empty=False):
    prompt = tokenizer.encode("Inspect and repair the current Python workspace.\n", add_special_tokens=False)
    first = tokenizer.encode("Inspect code.\n", add_special_tokens=False)
    observation = tokenizer.encode("File updated.\n", add_special_tokens=False)
    second = tokenizer.encode("Review the modified function.\n", add_special_tokens=False)
    response = first + observation + second
    p_len, r_len = len(prompt), len(response)
    ids = torch.tensor([prompt + response] * 64, dtype=torch.long)
    mask = torch.tensor([[1] * len(first) + [0] * len(observation) + [1] * len(second)] * 64)
    data = {"input_ids": ids, "attention_mask": torch.ones_like(ids),
            "position_ids": torch.arange(ids.shape[1])[None].repeat(64, 1),
            "prompts": ids[:, :p_len].clone(), "responses": ids[:, p_len:].clone(),
            "response_mask": mask, "old_log_probs": torch.zeros(64, r_len),
            "rollout_log_probs": torch.zeros(64, r_len),
            "returns": torch.ones(64, r_len) * mask, "advantages": mask.float() * .1}
    non_tensor = {}
    if pi:
        initial = tokenizer.encode("[PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\nworkspace_delta: empty\n[/PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\n", add_special_tokens=False)
        edited = tokenizer.encode("[PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\npath: example.py\nkind: function\nname: f\ncurrent_source:\ndef f(x):\n    return x + 1\n[/PRIVILEGED_CURRENT_STRUCTURAL_DELTA]\n", add_special_tokens=False)
        records = [dict(actor_response_start_abs=p_len, actor_response_end_abs=p_len + len(first),
                        state_hash="A", pi_ids=[] if empty else initial, valid=True),
                   dict(actor_response_start_abs=p_len + len(first) + len(observation),
                        actor_response_end_abs=p_len + r_len, state_hash="B", pi_ids=[] if empty else edited, valid=True)]
        array = np.empty(64, dtype=object)
        array[:] = [records for _ in range(64)]
        non_tensor["pi_call_records"] = array
    return DataProto.from_dict(data, non_tensor, meta_info={"temperature": 1.0})


class SmokeRunner(TaskRunner):
    def run(self, config):
        original_fit = RayPPOTrainer.fit

        def smoke(trainer):
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(config.actor_rollout_ref.model.path, local_files_only=True)
            trainer.checkpoint_manager.sleep_replicas()
            print("PI_GPU_SMOKE_STAGE baseline_values", flush=True)
            baseline = trainer._compute_values(short_batch(tokenizer, pi=False)).batch["values"]
            print("PI_GPU_SMOKE_STAGE empty_pi_values", flush=True)
            empty = trainer._compute_values(short_batch(tokenizer, pi=True, empty=True)).batch["values"]
            torch.testing.assert_close(baseline, empty, atol=1e-5, rtol=1e-5)
            batch = short_batch(tokenizer)
            original = {k: v.clone() for k, v in batch.batch.items()}
            print("PI_GPU_SMOKE_STAGE structural_pi_values", flush=True)
            values = trainer._compute_values(batch)
            assert torch.isfinite(values.batch["values"]).all()
            batch = batch.union(values)
            print("PI_GPU_SMOKE_STAGE critic_update", flush=True)
            critic = trainer._update_critic(batch)
            print("PI_GPU_SMOKE_STAGE actor_update", flush=True)
            actor = trainer._update_actor(batch)
            for k, v in original.items():
                torch.testing.assert_close(batch.batch[k], v, atol=0, rtol=0)
            metrics = {**reduce_metrics(critic.meta_info["metrics"]), **reduce_metrics(actor.meta_info["metrics"])}
            metrics = {k: float(v) for k, v in metrics.items()}
            assert all(math.isfinite(v) for v in metrics.values()), metrics
            root = Path(os.environ["LEGO_RL_ROOT"])
            (root / "logs/gpu_smoke_result.json").write_text(json.dumps({
                "status": "passed", "synthetic_batch": True, "rows": 64,
                "actual_model": config.actor_rollout_ref.model.path, "sp_size": 8,
                "empty_pi_value_max_abs_diff": float((baseline - empty).abs().max()),
                "values_shape": list(values.batch["values"].shape), "metrics": metrics,
                "production_optimizer_updates": 0, "checkpoint_saved": False}, indent=2))
            print("PI_GPU_SMOKE_PASSED", json.dumps(metrics), flush=True)
            trainer._shutdown_dump_executor()
        RayPPOTrainer.fit = smoke
        try:
            return super().run(config)
        finally:
            RayPPOTrainer.fit = original_fit


@hydra.main(config_path="config", config_name="ppo_trainer", version_base=None)
def main(config):
    run_ppo(config, task_runner_class=ray.remote(num_cpus=1)(SmokeRunner))


if __name__ == "__main__":
    main()
