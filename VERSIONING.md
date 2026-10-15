# Repair-state PI v2 version management

Repository: https://github.com/Jay-Juice/Lego-RL-main

Branch: `codex/pi-repair-state-v2-20261015`, based on `03b63e47ce793312f626d65657291488815a44ae`.

This is an independent copy of `pi_sequential_1k_repro_20261012`. The parent remains untouched. `SOURCE_PROVENANCE.json` records its backup and unchanged-source verification. `TRAINABLE_SPEC.json` supersedes the earlier design proposal: all attention freezing and value-head initialization remain exactly as in SAO baseline. No final-eight-layer unfreeze, zero-head initialization, extra objective, or learning-rate change is included.

Track source, tests, recipe, concise validation summaries and checksums. Do not track credentials, model weights, datasets, checkpoints, raw trajectories, logs, `.deployment`, or unrelated user files. Inherited historical operational scripts are not the new experiment entry.

## Reconstructing the private runtime

The offline deployment uses the complete copied private runtime. `VERSION_SOURCE_SHA256.json` fingerprints it, including the unchanged model engines. The Git branch contains the application source and the two PI-specific verl overlays under `vendor_overrides`; it does not vendor the entire third-party library or shared venv. A clone alone is not a self-contained training environment.

Prepare the documented parent private checkout and existing pinned dependencies, then use `python utils/apply_pi_vendor_overrides.py` to preview the two source overlays and `--apply` to install them. The utility rejects unknown source hashes and symlinked/shared checkouts. Do not run a dependency installer or overwrite shared packages to reconstruct this experiment. `vendor_overrides/trainer_delta_from_1k.patch` makes the new trainer changes reviewable separately from inherited PI plumbing. Validate the full deployed runtime with `python utils/validate_pi_source.py`.

The supported local-site entry is `bash ops/run_phase.sh train`, **only after explicit launch authorization and outstanding distributed validation**. It selects the new config, verifies the source manifest and rejects occupied GPUs or an existing Ray runtime. `PI_RESUME_MODE=auto` requires a complete checkpoint from this experiment and never falls back to fresh initialization. Output/audit directories are unique per attempt; the checkpoint namespace remains stable. Historical scripts under `ops` are not supported launch entries.

## Recurring maintenance

Every Friday at 18:00 Asia/Shanghai, the thread heartbeat checks this branch and synchronizes only already committed, reviewed task changes. It does not stage unknown changes, modify `main`, force-push, merge, deploy, train, stop processes or delete artifacts. Unchanged states stay quiet. Training monitoring remains separate and is not resumed by this maintenance task.

AI-assisted implementation; human review is still required before merging. No upstream verl contribution is being proposed.
