# Dynamic PI research version

User authorization: 2026-10-28, an independent copy, unchanged PI budgets and SAO
recipe, iterative diagnostics, conditional fresh training only after admission.

Repository: https://github.com/Jay-Juice/Lego-RL-main.git
Branch: codex/icps-dynamic-state-20261028
Parent reviewed ICPS archive: 823ac025303c3e5b6a829d326edce0a5aa5f127b
Local Git worktree: versioning/icps-dynamic-state-20261028
Source authority: experiments/icps_dynamic_state_v1_20261028

The old ICPS experiment and its branch are preserved. This candidate currently
has a frozen input selector and an opt-in runtime with actual proxy CPU checks.
Real cached Harbor and proxy lifecycle checks pass. Full two-phase Hydra comparison
and actual-tokenizer GPU-fixture CPU checks pass. Eight-GPU launch/rank audit, broader
source review and resource admission remain pending; the original disk reserve is
not met. No GPU update or training has run.
The inherited start_full97.sh is disabled (exit 78); inherited preparation
scripts are references, not supported launch commands. No new training has run.

Track reviewed source, tests, admission criteria, aggregate results and hashes.
Exclude model weights, datasets, raw trajectories, private labels and captures,
logs, caches, credentials, deployment evidence and unrelated files. A clone
needs the already pinned private offline environment; do not install or modify
shared dependencies. All 607 historical tasks are development, not a new test
set. Development labels are inaccessible to the generator via Landlock.

Recurring maintenance may push only reviewed committed changes on this branch.
Do not stage unknown files, change main, force-push, merge or launch training
as part of version maintenance. A draft PR is a review record, not approval to
train. ADMISSION_PLAN.md governs the separate conditional training decision.

Receipt-consumer follow-up: eleven local and eleven Linux CPU contracts pass.
No approved receipt or GPU launch exists. The five-file consumer manifest is
validation/GPU_LAUNCH_GATE_R6_CONTRACTS.sha256; earlier GPU preparation manifests
bind historical probe bytes preserved under archive/r6_before_launch_gate.

Rank-audit follow-up: probe-only subclasses add a blocking ONE_TO_ALL read-only
audit. Nine Linux CPU contracts and thirteen selected native-file comparisons
pass; real rank execution and complete source/launch admission remain pending.
Latest manifest: validation/GPU_RANK_AUDIT_R6_CONTRACTS.sha256. Prior receipt
consumer manifest binds probe bytes preserved in archive/r6_before_rank_audit.

Private-Ray lease implementation: eight Linux CPU contracts pass in the R2 queue.
The first queue exited1 on an unrelated older process environment permission error;
its source/manifest and logs are preserved. Start-time-first inspection skips older
processes; newer unreadable candidates still fail closed. A real owned Python child
was detected and exited by stdin EOF. No Ray/GPU was initialized and no signal sent.
The probe now requires explicit local Ray kwargs and holds the native shared flock
through receipt consumption and shutdown. Old config alone fails closed; producer,
complete manifest policy, updated whole-Hydra parity and actual Ray lifecycle remain
pending. Latest manifest: validation/GPU_PRIVATE_RAY_R6_CONTRACTS.sha256. Prior rank
manifest binds the archived probe in archive/r6_before_private_ray.

Private config preparation now recomposes current native Hydra trees with the
archived actual commands and verifies exact agreement with the pinned resolved
reference. Only two output paths and five explicit local-Ray fields change.
Whole-config comparison against both historical packing phases and agent YAML
byte identity pass. Five Linux CPU negative contracts pass; no run directory,
receipt, Ray instance, CUDA or model update was created. The first queue failed
an overstrict import-presence assertion; its evidence is preserved. Native config
plugins import Ray without initialization, now explicitly checked. See
GPU_PRIVATE_CONFIG_R6_CONTRACTS.json and its seven-input SHA manifest. Producer,
complete environment/dependency/asset policy and actual Ray/GPU acceptance remain
pending. Earlier private-Ray source manifest remains valid (probe unchanged).

Native source inventory expands beyond the earlier thirteen selected files:
633 inherited Python/YAML files across three trees, 614 equal, six modified
existing files and thirteen PI helper/diagnostic additions. Existing-file diffs
were inspected and classified. Actual native head registration, shared VeOmni
body origin and five OpSlot identities were checked without model construction.
5027 loaded module-file origins/hashes remain remote; this observed import closure
is a lower bound, not complete lazy/native dependency coverage. No whole-source
launch approval, Ray/CUDA initialization or GPU update was issued. See
GPU_NATIVE_INVENTORY_R6.json and GPU_NATIVE_SOURCE_R6_REVIEW.json. Complete manifest
policy, producer/environment and actual Ray lifecycle remain pending.

Offline asset preparation (2026-10-28): twelve Linux CPU contracts and readonly
hashing of 18 actual cached files pass. Four safetensors shards/775 tensor headers
match the exact index/layout/total bytes; tokenizer/chat template/config and the
two original parquet identities are bound. Parquet rows/labels were not read.
The entire inspection/hash pass rejects metadata/file-set drift, symlinks and
mid-pass mutations. First eleven-contract Linux pass is preserved before this
strengthening; local Windows strict-resolve permission errors are not a pass.
See GPU_OFFLINE_ASSETS_R6_CONTRACTS_R2.json and GPU_OFFLINE_ASSETS_R6_REVIEW.json.
The private manifest remains remote. This new component is not yet integrated
with the receipt consumer. Native/shared/lazy dependency policy, reviewed producer
and real Ray/GPU acceptance remain pending; no admission or GPU update occurred.
The current five-input GPU_OFFLINE_ASSETS_R6_CONTRACTS.sha256 binds the R2 source.

2026-10-28 user steering: prioritize actual GPU validation or PI information design, not continued generic audit expansion. Fresh resources now pass: 506.972GiB free versus 426.911GiB required, eight GPUs idle and required ports available. This observation is not a launch receipt and must be refreshed before launch. R6 remains frozen; separate R7 design records three synthetic candidate omissions. No GPU/model update or training admission yet.
