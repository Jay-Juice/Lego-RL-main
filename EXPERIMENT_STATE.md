# Repair-state PI v2

Code implemented; CPU/Harbor validated; distributed acceptance pending. **Training remains stopped.**

Current branch: `codex/pi-repair-state-v2-20261015`. Parent: `pi_sequential_1k_repro_20261012`; all 3,824 parent files rechecked unchanged. SOURCE_PROVENANCE.json records its backup.

PI changes: baseline-to-current before/after hunks, bounded static context, already Actor-visible completed tool evidence, separate code/status deduplication and causal PI-only quota. No extra task tests, oracle, future observations or LLM summaries.

SAO training unchanged: native head initialization, original attention/vision freeze patterns, learning rates, batch/epochs, loss, reward, GAE and Actor update timing. Full 130-argument launch command differs only in experiment name.

Persistence: full warmup checkpoints at 5 and 10; existing 20/every10/final saves retained. Complete-shard gate, strict same-experiment resume, 200GiB free-space wait, unique attempt outputs; no automatic deletion.

Validation: 40 CPU tests passed; real Harbor plus existing Qwen tokenizer/scripted output integration passed; 3,573 runtime SHA checks passed. Full evidence scope is in VALIDATION_SUMMARY.json. Pending before formal launch: 9B/SP8 numerical acceptance and full distributed warmup save/load/next-batch continuity. CPU tests do not replace these.

Independent remote root: `/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015`. Specification: TRAINABLE_SPEC.json. Version procedures: VERSIONING.md. Inherited historical ops are provenance, not current launch entries. Supported entry: ops/run_phase.sh with the new config, only after launch authorization.

GitHub maintenance runs Friday 18:00 Asia/Shanghai, synchronizing only checked, already committed work. No automatic merge, deployment or training.
