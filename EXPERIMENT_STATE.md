# Repair-state PI v2

Code implemented; CPU/Harbor validated; distributed acceptance pending. **Training remains stopped.**

Current branch: `codex/pi-repair-state-v2-20261015`. Parent: `pi_sequential_1k_repro_20261012`; all 3,824 parent files rechecked unchanged. SOURCE_PROVENANCE.json records its backup.

PI changes: baseline-to-current before/after hunks, bounded static context, already Actor-visible completed tool evidence, separate code/status deduplication and causal PI-only quota. No extra task tests, oracle, future observations or LLM summaries.

SAO training unchanged: native head initialization, original attention/vision freeze patterns, learning rates, batch/epochs, loss, reward, GAE and Actor update timing. Full 130-argument launch command differs only in experiment name.

Persistence: full warmup checkpoints at 5 and 10; existing 20/every10/final saves retained. Complete-shard gate, strict same-experiment resume, 200GiB free-space wait, unique attempt outputs; no automatic deletion.

Validation: 40 CPU tests passed; real Harbor plus existing Qwen tokenizer/scripted output integration passed; 3,573 runtime SHA checks passed. Full evidence scope is in VALIDATION_SUMMARY.json. Pending before formal launch: 9B/SP8 numerical acceptance and full distributed warmup save/load/next-batch continuity. CPU tests do not replace these.

Independent remote root: `/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015`. Specification: TRAINABLE_SPEC.json. Version procedures: VERSIONING.md. Inherited historical ops are provenance, not current launch entries. Supported entry: ops/run_phase.sh with the new config, only after launch authorization.

GitHub maintenance runs Friday 18:00 Asia/Shanghai, synchronizing only checked, already committed work. No automatic merge, deployment or training.


## 2026-10-15 eight-GPU acceptance and authorized automatic training

User explicitly authorized all eight GPUs and immediate formal training after acceptance. At 20:48 CST, screen `lego-piv2-accept-train-20261015` started `ops/acceptance_then_train_20261015.sh`. Queue: `logs/acceptance_v2_20261015`. Deployment SHA: 3576 runtime files; 14 v2 CPU regressions, bash syntax and actual launch dryrun/preflight passed. Eight GPUs were idle, no Ray; D1 free 344064806912 bytes. Model loading is observed, acceptance not yet passed.

Validation uses real Qwen3.5-9B/SP8/logical64 but short synthetic trajectories. It saves an isolated full checkpoint labeled step10 after ONE synthetic Critic update, with zero Actor updates; this is not ten production steps. It restores Actor/Critic state and compares next real dataloader batch, restored values, and the next Critic update against uninterrupted execution; then checks Actor update. All validation updates are discarded. This is not an efficacy evaluation or maximum-length GPU stress test. Validation EXP `pi-v2-acceptance-20261015-r1`; formal EXP remains `sao-qwen35-9b-b64-pi-repair-state-v2-20261015`.

Supervisor requires result/exit/source-SHA acceptance and idle GPUs/no Ray/200GiB free before formal fresh start. Checkpoints retained; no automated asset deletion. Validation source backup `experiments/backups/pi_v2_before_8gpu_acceptance_20261015.zip`, CRC passed, SHA256 `faccf863ac98ba44eb77752f51dc72c6be0bfebb6799d41f466634caf4adecdb`. Existing heartbeat resumed for this v2 only, every30min. Actual formal launch still pending.


### User update during acceptance: save only extra step10
User removed step5 warmup saving. The only runtime change during the current validation is the future launch config `PI_WARMUP_CHECKPOINT_STEPS=5,10` -> `10`; no imported Python/model code changed. Local pre-change config/manifest retained in `.deployment/step10_only_20261015`. Deployed via reviewed WSL rsync, 3576 SHA pass. Loaded validation remains on old manifest bbc5d68c0312eeb3806b1f48475f61bbe5df8762076bdf26a7e97f10d7127ee5; new manifest33e4701e259c2db118ed9df84049c87e2c97d0d699d47d3ed3a5a87da47b8545. Its synthetic save was always only step10. The original supervisor source gate will intentionally stop after successful validation because the launch config changed. After acceptance result/exit pass, verify the ONLY source delta is this requested save schedule, then launch formal training directly with new config and idleGPU/noRay/200GiB gates. Do not rerun successful GPU validation merely for a save-time deletion. Formal checkpoints:10,20,30,... and final; Actor warmup unchanged.
