# ICPS v1.1 full97 r2 — source archive, 2026-10-27

Repository: https://github.com/Jay-Juice/Lego-RL-main

Branch: `codex/icps-v11-20261027`, based on the reviewed repair-state application
commit `45d697448bdc910bb12c51a1eaaa66d4b0362090`. This branch records a different
PI method; it does not rename old repair-state results as ICPS results. The root
`VERSIONING.md` and old experiment documents remain historical records.

## What is preserved

`experiments/icps_v11_full97_sao_20261024_r2/` contains the exact Windows-authoritative
ICPS source, tests, initial and resume launch recipes, import overlays, and source
checksums. `ICPS_SOURCE_MANIFEST.json` records every added runtime file's byte hash.
The inherited application source is already present at the base commit.

`vendor_runtime/verl/verl/` and `vendor_runtime/harbor/src/` preserve the complete
importable private library trees, including package templates/configuration and
their licenses. This includes the local PI padding/engine integration that cannot
be reproduced by installing an arbitrary upstream verl release. These are source
archives, not instructions to overwrite a shared environment.

Excluded: datasets, model/checkpoint weights, raw trajectories, benchmark results
per task, logs, deployment evidence, container inventories, credentials, caches,
and compiled/shared environment packages. The two JSON files inside Harbor's
CLI template-adapter are source templates, not collected dataset records.

## Runtime and reconstruction boundary

The historical launch files intentionally retain their site paths and experiment
identity. Merely cloning this branch must NOT start training. A new deployment
requires a separate private directory, the inherited app source from this commit,
the archived private library trees under `third_party/verl` and `third_party/harbor`,
and an already provisioned compatible offline environment. Copying the library
trees must be previewed and must reject nonempty/unrecognized targets. Existing
running checkouts must never be overwritten.

The shared VeOmni/vLLM/FLA stack is not vendored here. Observed package versions
are in `ICPS_ENVIRONMENT_VERSIONS.json`; version strings alone do not prove
identical patched binaries or bitwise reproducibility. Model tokenizer files,
the prepared task dataset and image identities remain external private assets.
Run the archived `prepare_full.py` only for a newly authorized experiment to
create its machine-local inventory and namespace; it is not a continuation command.

Current historical continuation entry is
`experiments/icps_v11_full97_sao_20261024_r2/ops/resume_after_eval_20261027_r2/start.sh`.
The earlier `resume_after_eval_20261027` queue failed its evaluation-completion
gate before training; it is retained for source history and is not current.
No archive script invokes either entry. Continuations require the same experiment's
complete checkpoint, never a fresh fallback.

## Training recipe and known limitations

- Native value head and attention/visual freeze match the SAO recipe. No last-eight
  layer unfreeze, head initialization trick, extra loss or reward shaping.
- 6248 rows, batch/mini64, 97 steps, workers32, SP8; Actor/Critic epochs1/2;
  LR1e-6/5e-6; first Actor update/save20; save every10 and final97; no warmup save.
- ICPS: issue-only fixed top3; pre-action real source windows; initial192,
  update128, episode4096 tokens; Critic only. Actor history, mask and reward remain
  on their original timeline.
- Historical packing is explicit: steps1–20 Actor14336/Critic20480; steps21–97
  Actor16384/Critic45056. Native inference/logprob budgets remain unchanged.
  This mirrors the historical SAO resume20 change; it is not a PI quota switch.
- The three serializer limitations found on Oct27 are deliberately NOT silently
  repaired in this archive: small remaining-budget stall, omitted missing-candidate
  status, and stale source_hash on one-line fallback. An eventual correction must
  be a separately reviewed version. The running source remains unchanged.
- Numeric repeat/update reproducibility remains unresolved. Matching source and
  checkpoint inventory is not a bitwise-resume guarantee.

## Validation and results

Local archived-source tests and manifest verification are recorded in the commit
description/validation record. Historical CPU/native API/Harbor validations and
actual completed steps are summarized without uploading private logs.

Verified500 original passes: ICPS20=273, ICPS30=268, ICPS40=280; SAO20=262,
SAO30=286, SAO40=291. ICPS40 and SAO30/40 have499 scored cases; other groups500.
Exception supplements remain independent and are not combined as best-of scores.
Single stochastic runs, service failures, and historical runtime differences mean
these are not strict causal single-variable estimates.

The frozen-Critic contrast is a separate diagnostic task. Its source and reports
must distinguish CPU cache validation, pending GPU work, and actual model results.
No training resume/stop/deploy is authorized by version maintenance itself.
