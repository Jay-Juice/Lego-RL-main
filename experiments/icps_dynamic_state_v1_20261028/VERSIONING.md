# Dynamic PI research version

User authorization: 2026-10-28, an independent copy and unchanged native SAO
recipe. Later direct instruction permits modest experimental PI budget increases;
frozen R6/runtime remains192/128/4096. Fresh training is conditional on admission.

Repository: https://github.com/Jay-Juice/Lego-RL-main.git
Branch: codex/icps-dynamic-state-20261028
Parent reviewed ICPS archive: 823ac025303c3e5b6a829d326edce0a5aa5f127b
Local Git worktree: versioning/icps-dynamic-state-20261028
Source authority: experiments/icps_dynamic_state_v1_20261028

The old ICPS experiment and its branch are preserved. This candidate currently
has a frozen input selector and an opt-in runtime with actual proxy CPU checks.
Real cached Harbor and proxy lifecycle checks pass. Full two-phase Hydra comparison
and actual-tokenizer GPU-fixture CPU checks pass. Actual private Ray CPU init/task/shutdown now passes with no owned leftovers.
The original disk reserve and eight-idle-GPU snapshot pass after user cleanup.
Native eight-GPU disposable updates now PASS at packing phases20/21; the bounded
producer/evidence binding is implemented. See GPU_SHORT_R6_RESULT/REVIEW.json.
No formal training or checkpoint save/reuse has occurred.
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

Actual private Ray follow-up: first attempt failed because installed Ray chmods its
supplied temp root0777. Preserve that attempt and archive/r6_live_ray_directory_mode_failure.
The minimal fix places Ray in a child below the existing private0700 parent.
R2 actual local init/CPU task/shutdown passes; tagged process scan has no leftovers.
Fourteen affected Linux CPU contracts and full two-phase Hydra parity pass.
Latest validation/GPU_PRIVATE_RAY_R6_LIVE.sha256 binds nine inputs; earlier lease/config
manifests bind pre-fix archived bytes. No GPU/model/optimizer update or production
receipt exists. Continue the bounded eight-GPU launch path, not generic expansion.

Actual eight-GPU short test completed in gpu-r6-c4000612667ac86e, exit0. Both native
roles have finite positive gradients and finite values/losses; empty PI and Actor
PI-on/off comparisons are exact. Actual rank/head/freeze/optimizer membership
passes before/after; own Ray/GPU teardown is verified. Four earlier failed
attempts and source archives remain. Probe-only MFU compatibility handles missing
telemetry; native math and frozen method unchanged. Latest17-input launcher
manifest is GPU_LAUNCH_R6.sha256. Earlier changed-probe manifests are historical.
Existing reviewed evidence scope is explicit, not full transitive approval.
Formal training remains separately gated and its entry disabled.

R7 W0 candidate-pool/budget factorial:607 development inputs,366 exact mapped
targets. Pool3 caps192/256/384 visible171/179/189, full105/128/159; pool6
candidate recall282 vs242 but visible166/170/183. R2 exit0 with four CPU shards,
per-file baseline grants and three actual label denials,607 baseline/prefix checks.
Original overly broad baseline directory grant and queue preserved; not accepted
as complete isolation evidence. No R6 runtime/confirmation or GPU changes.
Pool3/256 is only a next-development comparator. See R7_BUDGET_RESULTS.md and
BUDGET_ABLATION_R7_REVIEW.json. Private per-case payloads/receipts are excluded.

R7 window research completed in a separate prototype: five new rules plus two
controls at256 tokens/max3 windows,607 development inputs. diverse6 gives
197visible/130full vs baseline179/128 with249.76 vs246.91 mean tokens.
rank6 gives188/137 and+4.93% target-line density; diverse6 density only+0.37%.
Atomic/compact negative results retained. Four actual label denials,607 exact
baseline outputs, source/cap/roundtrip checks and exit0. No R6 runtime, GPU or
confirmation changes. See WINDOW_RESEARCH_R7_REVIEW.json and results document.
