"""CPU-only real Harbor/proxy integration check; scripted actions and fake generation."""
import asyncio
import json
import os
import shlex
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from harbor.agents.base import BaseAgent


class PIProbeAgent(BaseAgent):
    @staticmethod
    def name(): return "pi-probe"
    def version(self): return "1"
    async def setup(self, environment): pass

    async def run(self, instruction, environment, context):
        from transformers import AutoTokenizer
        from verl.workers.rollout.replica import TokenOutput
        from verl_patch.agent_loop.vllm_chat_completion_proxy import _VLLMChatCompletionsProxy
        from verl_patch.agent_loop.privileged_critic_builder import interleave
        tokenizer = AutoTokenizer.from_pretrained(os.environ["PI_PROBE_MODEL"], local_files_only=True)
        sid = environment.session_id
        audit = []

        class Manager:
            async def generate(self, request_id, prompt_ids, sampling_params):
                audit.append({"generate_started_ns": time.time_ns(), "actor_prompt_ids": list(prompt_ids)})
                ids = tokenizer.encode(f"Inspect current workspace, call {len(audit)}.", add_special_tokens=False)
                return TokenOutput(token_ids=ids, log_probs=[-0.1] * len(ids), stop_reason="length")

        loop = SimpleNamespace(tokenizer=tokenizer, processor=None, server_manager=Manager(),
                               loop=asyncio.get_running_loop(), apply_chat_template_kwargs={})

        async def template(messages, tools=None, remove_system_prompt=False):
            from verl.utils.chat_template import apply_chat_template, initialize_system_prompt
            ids = apply_chat_template(tokenizer, messages, tools=tools, tokenize=True, add_generation_prompt=True)
            if remove_system_prompt:
                ids = ids[len(initialize_system_prompt(tokenizer)):]
            return ids
        loop.apply_chat_template = template
        proxy = _VLLMChatCompletionsProxy(loop, "qwen3_coder", max_consecutive_no_tool=0)
        await proxy.open_session(sid, self.logs_dir)
        messages = [{"role": "user", "content": "Inspect the current task workspace."}]
        capture = environment._pi_baseline
        root = capture["repo_root"]
        target = root + "/src/jinja2/debug.py"
        read = await environment.exec(command="cat " + shlex.quote(target))
        assert read.return_code == 0
        original = read.stdout

        async def write(text):
            command = '"${HARBOR_VERIFIER_PYTHON:-python3}" -c ' + shlex.quote(
                "from pathlib import Path;Path(" + repr(target) + ").write_text(" + repr(text) + ")")
            result = await environment.exec(command=command)
            assert result.return_code == 0, result.stderr

        async def call(label):
            if len(messages) > 1:
                messages.append({"role": "user", "content": label})
            message, *_ = await proxy._generate_assistant_message(sid, messages, None, {"temperature": 1.0, "max_tokens": 16})
            messages.append(message)
            pi = proxy._sessions[sid]["pi_call_records"][-1]
            assert pi["captured_at_end_ns"] <= audit[-1]["generate_started_ns"]
            # Actor sees exactly its chat history; PI is exclusively an out-of-band record.
            generated = tokenizer.encode(f"Inspect current workspace, call {len(audit)}.", add_special_tokens=False)
            assert audit[-1]["actor_prompt_ids"] == proxy._sessions[sid]["rolling_acc_ids"][:-len(generated)]
            return pi

        try:
            # Exercise the real tokenizer/proxy capture with SDK-decoded dict
            # arguments and an actual harmless completed tool observation.
            command = "printf '2 passed\\n'"
            observed = await environment.exec(command=command)
            assert observed.return_code == 0
            messages.extend([
                {"role": "assistant", "content": "", "tool_calls": [{"id": "probe-dict-call", "type": "function", "function": {"name": "terminal", "arguments": {"command": command}}}]},
                {"role": "tool", "tool_call_id": "probe-dict-call", "content": json.dumps({"exit_code": observed.return_code, "output": observed.stdout})},
            ])
            initial = await call("initial")
            assert initial["execution_evidence"]["status"] == "completed_observation"
            assert initial["execution_evidence"]["test_report"] == "unknown"
            assert not proxy._sessions[sid].get("pi_error")
            lookup = await environment.exec(command="ls >/dev/null && cat " + shlex.quote(target) + " >/dev/null")
            assert lookup.return_code == 0
            readonly = await call("read only")
            assert initial["state_hash"] == readonly["state_hash"]
            # Change a business function without inspecting tests, injected locations or oracle assets.
            assert 'def get_template_locals(' in original
            changed = original.replace('def get_template_locals(', 'def get_template_locals(', 1)
            lines = changed.splitlines(keepends=True)
            from harbor_patch.privileged_state.structural_lift import scopes
            scope = next(e for e in scopes(changed) if e["qualname"] == "get_template_locals")
            # Add a harmless real edit inside the function's current body; tests are never invoked.
            position = scope["start_line"]
            while not lines[position - 1].rstrip().endswith(":"):
                position += 1
            lines.insert(position, '    _pi_probe_current_state = 1\n')
            await write("".join(lines))
            edited = await call("business function edited")
            assert edited["state_hash"] != initial["state_hash"]
            assert '_pi_probe_current_state = 1' in edited["pi_text"]
            assert 'get_template_locals' in edited["pi_text"]
            await write(original)
            restored = await call("restored")
            assert restored["state_hash"] == initial["state_hash"]
            await write("def broken(:\n    pass\n")
            syntax = await call("temporary syntax error")
            assert syntax["parse_failure_count"] == 1
            await write(original)
            # Force a history rebuild retaining only a known final assistant message.
            messages[:] = [messages[0], messages[-1], {"role": "user", "content": "retained message after compaction"}]
            compacted = await call("compaction")
            # A disposable probe reproduces missing Git objects without changing
            # the prepared tree. Keep the probe's original metadata for cleanup.
            await write("".join(lines))
            before_guard = await call("edit before metadata loss")
            saved_git = "/tmp/pi-probe-original-git-" + sid
            import shutil
            replace_code = "import os,subprocess;os.rename(" + repr(root + "/.git") + "," + repr(saved_git) + ");subprocess.run(['git','-C'," + repr(root) + ",'init','-q'],check=True)"
            changed_git = await environment.exec(command='"${HARBOR_VERIFIER_PYTHON:-python3}" -c ' + shlex.quote(replace_code))
            assert changed_git.return_code == 0, changed_git.stderr
            try:
                guarded = await call("same workspace after git reinit")
                assert guarded["baseline_observer_used"] is True
                assert guarded["baseline_sha"] == before_guard["baseline_sha"]
                assert guarded["state_hash"] == before_guard["state_hash"]
                assert guarded["code_ids"] == before_guard["code_ids"]
            finally:
                restore_code = "import os,shutil;shutil.rmtree(" + repr(root + "/.git") + ");os.rename(" + repr(saved_git) + "," + repr(root + "/.git") + ")"
                restored_git = await environment.exec(command='"${HARBOR_VERIFIER_PYTHON:-python3}" -c ' + shlex.quote(restore_code))
                assert restored_git.return_code == 0
                await write(original)
            from harbor_patch.privileged_state import registry
            from verl_patch.agent_loop.vllm_chat_completion_proxy import _proxy_error_from_exception
            count_before = len(audit)
            registry.unregister(sid)  # same lifecycle transition as environment.stop
            try:
                try:
                    await call("late request after environment unregister")
                    raise AssertionError("closed request generated")
                except registry.SessionClosedError as exc:
                    assert _proxy_error_from_exception(exc).status == 410
                assert len(audit) == count_before
                assert not proxy._sessions[sid].get("pi_error")
                assert proxy._sessions[sid]["pi_closed_requests"] == 1
            finally:
                registry.register(sid, environment.capture_structural_delta)
            meta = await proxy.pop_session(sid)
            actor = meta["traj_acc_ids"]
            ids, mapping, mask = interleave(actor, meta["initial_prompt_token_len"], meta["traj_response_mask"], meta["pi_call_records"], total_pi_budget=172032, tokenizer=tokenizer)
            assert len(mapping) == len(meta["traj_response_mask"])
            assert [token for token, privileged in zip(ids, mask) if not privileged] == actor
            for offset, position in enumerate(mapping):
                assert ids[position + 1] == actor[meta["initial_prompt_token_len"] + offset]
            assert all(len(record["pi_ids"]) <= 2048 for record in meta["pi_call_records"])
            result = {"status": "passed", "actual_model": False, "verifier_run": False,
                      "decoded_dict_real_proxy_passed": True, "baseline_guard_reinit_equal": True, "closed_request_rejected_without_generation": True, "generate_calls": len(audit), "initial_empty": not initial["changed_files"],
                      "readonly_equal": True, "business_edit_seen": True, "restore_equal": True,
                      "syntax_fallback": True, "history_rebuild": True, "actor_tokens": len(actor),
                      "critic_tokens": len(ids), "pi_tokens": sum(mask),
                      "calls": audit, "records": meta["pi_call_records"]}
            (self.logs_dir / "pi_probe_result.json").write_text(json.dumps(result, indent=2))
        finally:
            await proxy.stop()


async def main():
    from harbor.models.trial.config import TrialConfig
    from harbor.trial.trial import Trial
    root = Path(__file__).resolve().parents[1]
    sid = "pi-integration-" + uuid4().hex[:10]
    cfg = TrialConfig.model_validate({
        "task": {"path": "/media/ubuntu/D1/zsj/Lego-RL-main/data/swesmith_python_full_v7_verdict_v6_20260930/pallets__jinja.ada0a9a6.func_pm_remove_cond__0r1sepln"},
        "trial_name": sid, "trials_dir": str(root / "harbor_trials/integration"),
        "agent": {"import_path": "utils.pi_repair_state_final_probe_20261016:PIProbeAgent", "override_timeout_sec": 240},
        "predict_patch": {"enabled": True, "init_baseline": True, "repo_paths": ["/testbed"], "baseline_tag": "harborbaseline"},
        "verifier": {"enabled": False},
        "environment": {"import_path": "harbor_patch.environments.pooled_remote_docker:PooledRemoteDockerEnvironment",
                        "force_build": True, "delete": False, "override_cpus": 2, "override_memory_mb": 8192,
                        "kwargs": {"verifier_runtime_image": "lego-rl/swebench-verifier-runtime:4.0.3-py311",
                                   "verifier_runtime_mount_path": "/opt/lego-verifier",
                                   "verifier_runtime_image_subpath": "opt/lego-verifier"}}})
    trial = await Trial.create(cfg)
    result = await trial.run()
    path = root / "logs" / "harbor_repair_state_final_20261016_result.json"
    with path.open("x") as handle:
        handle.write(result.model_dump_json(indent=2))
    if result.exception_info:
        raise RuntimeError(result.exception_info.model_dump_json())
    print(json.dumps({"status": "passed", "trial": sid, "result": str(path)}))


if __name__ == "__main__":
    asyncio.run(main())
