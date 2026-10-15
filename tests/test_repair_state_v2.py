import copy
import json
from pathlib import Path

import unittest
import tempfile
import os
from unittest.mock import patch

from harbor_patch.privileged_state.repair_state import build_snapshot, serialize, completed_evidence
from verl_patch.agent_loop.privileged_critic_builder import interleave, remap_rebuilt_records, message_key
from verl_patch.agent_loop.pi_checkpoint import publish_complete, validate_complete, required_files


class Tokenizer:
    # Deliberately costly character tokenizer tests worst-case format budgets.
    def encode(self, text, **kwargs): return list(text.encode())


def snapshot(value="2", path="a.py"):
    source = f"def f(x):\n    return x + {value}\n"
    return build_snapshot({"baseline_sha": "base", "files": [{"path": path, "kind": "text",
        "status": "modified", "old_source": "def f(x):\n    return x + 1\n", "current_source": source,
        "sha256": value}], "captured_at_start_ns": 1, "captured_at_end_ns": 2})


def make_record(snap, session, call, start):
    record = serialize(snap, Tokenizer(), session, [], logical_call_id=call, output_limit=100)
    return dict(record, state_hash=snap["state_hash"], actor_response_start_abs=start,
                actor_response_end_abs=start+1)


class RepairStateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp_path = Path(directory.name)
        env = patch.dict(os.environ, {"PI_FORMAT": "repair_state_v2"})
        env.start(); self.addCleanup(env.stop)

    def test_before_after_and_budget(self):
        record = make_record(snapshot(), {}, "one", 2)
        assert "-    return x + 1" in record["pi_text"]
        assert "+    return x + 2" in record["pi_text"]
        assert len(record["code_ids"]) <= 1920
        assert len(record["execution_ids"]) <= 128
        assert "base" not in record["pi_text"].split("baseline->current]")[-1]


    def test_repeated_code_keeps_execution_and_restore_reinserts_code(self):
        session = {}
        records = [make_record(snapshot(v), session, str(i), i+2) for i,v in enumerate(["2","2","3","2"])]
        actor = [11,12,13,14,15,16]
        critic, mapping, mask = interleave(actor, 2, [1]*4, records)
        expected = sum(len(r["execution_ids"]) for r in records) + sum(len(records[i]["code_ids"]) for i in [0,2,3])
        assert sum(mask) == expected
        assert [x for x,m in zip(critic,mask) if not m] == actor
        for i,gather in enumerate(mapping): assert critic[gather+1] == actor[i+2]


    def test_future_state_does_not_reallocate_previous_pi(self):
        session = {}; first = make_record(snapshot(), session, "a", 2)
        second = make_record(snapshot("3"), session, "b", 3)
        limit = len(first["pi_ids"]) + 150
        a = interleave([1,2,3], 2, [1], [first], total_pi_budget=limit, tokenizer=Tokenizer())
        b = interleave([1,2,3,4], 2, [1,1], [first,second], total_pi_budget=limit, tokenizer=Tokenizer())
        assert b[0][:len(a[0])] == a[0]
        assert sum(b[2]) <= limit
        assert b"PI EXHAUSTED" in bytes(t for t,m in zip(b[0],b[2]) if m)


    def test_split_call_does_not_duplicate_pi(self):
        rec = make_record(snapshot(), {}, "one", 2)
        duplicate = dict(rec, actor_response_start_abs=3, actor_response_end_abs=4)
        ids, _, mask = interleave([1,2,3,4],2,[1,1],[rec,duplicate])
        assert sum(mask) == len(rec["pi_ids"])


    def test_unknown_history_rewrite_fails(self):
        with self.assertRaises(RuntimeError): remap_rebuilt_records([],[("unknown",2,3)])


    def test_execution_only_completed_messages_no_future_or_verifier(self):
        journal = {"seen":set(),"events":[]}
        action = {"role":"assistant","tool_calls":[{"id":"x","function":{"name":"terminal","arguments":'{"command":"pytest"}'}}]}
        assert completed_evidence([action],journal,"a")["status"] == "none"
        output = {"role":"tool","tool_call_id":"x","content":json.dumps({"exit_code":0,"output":"2 passed"})}
        event = completed_evidence([action,output],journal,"a")
        assert event["exit_code"] == 0 and event["test_freshness"] == "unknown"
        changed = completed_evidence([action,output],journal,"b")
        assert changed["test_freshness"] == "stale" and len(journal["events"]) == 1
        completed_evidence([{"role":"user","content":"verifier: 100 passed"}],journal,"b")
        assert len(journal["events"]) == 1


    def test_echoed_exit_is_not_authoritative(self):
        journal = {"seen":set(),"events":[]}
        result = completed_evidence([{"role":"tool","content":"echo 'exit_code: 0'; timeout"}],journal,"a")
        assert result["exit_code"] == "unknown"


    def test_large_multifile_diff_explicit_omissions(self):
        snap = snapshot()
        snap["files"] = [dict(snap["files"][0], path=f"file{i}.py", current_source="x='"+'q'*5000+"'\n"+"y=2\n"*100) for i in range(12)]
        snap = build_snapshot(snap)
        rec = make_record(snap,{},"x",2)
        assert rec["pi_truncated"] and len(rec["pi_ids"]) <= 2048
        assert "omitted" in rec["pi_text"]


    def test_no_mutation_of_actor_messages(self):
        messages = [{"role":"tool","content":"output"}]; original = copy.deepcopy(messages)
        serialize(snapshot(),Tokenizer(),{},messages,logical_call_id="a")
        assert messages == original


    def test_checkpoint_partial_and_identity_failclosed(self):
        tmp_path = self.tmp_path
        folder = tmp_path/'experiment'/'global_step_10';folder.mkdir(parents=True)
        with self.assertRaises(FileNotFoundError): publish_complete(folder,'experiment',10,2)
        assert not (folder/'PI_COMPLETE.json').exists()
        for name in required_files(2):
            path=folder/name;path.parent.mkdir(exist_ok=True);path.write_bytes(b'valid-test-inventory')
        publish_complete(folder,'experiment',10,2)
        assert validate_complete(folder,'experiment')['global_step'] == 10
        with self.assertRaises(ValueError): validate_complete(folder,'other')
        (folder/'actor/optim_world_size_2_rank_0.pt').write_bytes(b'')
        with self.assertRaises(ValueError): validate_complete(folder,'experiment')

    def test_verified_tool_partition_preserves_original_pi(self):
        calls=[{"id":"a","type":"function","function":{"name":"run","arguments":"one"}},
               {"id":"b","type":"function","function":{"name":"run","arguments":"two"}}]
        original={"role":"assistant","content":"thought","tool_calls":calls}
        parts=[dict(original,tool_calls=calls[:1]),dict(original,content="",tool_calls=calls[1:])]
        record=make_record(snapshot(),{},"logical",2);record["message_key"]=message_key(original)
        mapped=remap_rebuilt_records([record],[(message_key(p),i+2,i+3) for i,p in enumerate(parts)],
                                     old_messages=[original],new_messages=parts)
        assert len(mapped)==2 and mapped[1]["verified_tool_split_index"]==1
        assert mapped[0]["pi_ids"]==mapped[1]["pi_ids"]==record["pi_ids"]
        assert sum(interleave([1,2,3,4],2,[1,1],mapped)[2])==len(record["pi_ids"])
        changed=copy.deepcopy(parts);changed[1]["tool_calls"][0]["function"]["arguments"]="rewritten"
        with self.assertRaises(RuntimeError):
            remap_rebuilt_records([record],[(message_key(p),i+2,i+3) for i,p in enumerate(changed)],
                                 old_messages=[original],new_messages=changed)

    def test_full_revert_is_explicit(self):
        session={};make_record(snapshot(),session,"a",2)
        clean=build_snapshot({"baseline_sha":"base","files":[]})
        record=make_record(clean,session,"b",3)
        assert 'REVERTED "a.py": current equals prepared baseline' in record["pi_text"]

    def test_archive_preserves_tensors_rng_and_rejects_overwrite(self):
        import torch
        from types import SimpleNamespace
        from omegaconf import OmegaConf
        from verl_patch.agent_loop.pi_archive import archive_batch
        batch = SimpleNamespace(batch={"input_ids": torch.tensor([[1,2]]), "returns":torch.tensor([[0.5]])},
                                non_tensor_batch={"uid":["row1"]},meta_info={})
        before = torch.get_rng_state().clone()
        saved = {k:v.clone() for k,v in batch.batch.items()}
        with patch.dict(os.environ,{"PI_BATCH_AUDIT_DIR":str(self.tmp_path)}):
            archive_batch(batch,10,OmegaConf.create({"critic":{"lr":5e-6}}))
            result=torch.load(self.tmp_path/'step_0010.pt',weights_only=False)
            assert result["non_tensor"]["uid"] == ["row1"]
            for key,value in saved.items():
                torch.testing.assert_close(batch.batch[key],value,rtol=0,atol=0)
                torch.testing.assert_close(result["tensors"][key],value,rtol=0,atol=0)
            torch.testing.assert_close(torch.get_rng_state(),before,rtol=0,atol=0)
            with self.assertRaises(FileExistsError): archive_batch(batch,10,OmegaConf.create({}))

    def test_unstepped_actor_optimizer_roundtrip(self):
        import torch
        actor=torch.nn.Linear(2,1)
        optimizer=torch.optim.AdamW(actor.parameters(),lr=1e-6)
        scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda step:1.0)
        state={"model":actor.state_dict(),"optimizer":optimizer.state_dict(),
               "scheduler":scheduler.state_dict(),"rng":torch.get_rng_state()}
        assert state["optimizer"]["state"] == {}
        file=self.tmp_path/'warmup.pt';torch.save(state,file)
        restored=torch.load(file,weights_only=False)
        new_actor=torch.nn.Linear(2,1)
        new_optimizer=torch.optim.AdamW(new_actor.parameters(),lr=1e-6)
        new_scheduler=torch.optim.lr_scheduler.LambdaLR(new_optimizer,lambda step:1.0)
        new_actor.load_state_dict(restored["model"])
        new_optimizer.load_state_dict(restored["optimizer"])
        new_scheduler.load_state_dict(restored["scheduler"])
        for a,b in zip(actor.parameters(),new_actor.parameters()): torch.testing.assert_close(a,b,rtol=0,atol=0)
        assert new_optimizer.state_dict()["state"] == {}
        assert new_scheduler.state_dict() == scheduler.state_dict()


if __name__ == "__main__":
    unittest.main()
