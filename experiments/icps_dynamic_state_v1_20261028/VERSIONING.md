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

R7 candidate recall follow-up: four retrieval hypotheses plus exact diverse6 control, same607development inputs and256/max3window allocator. pool12 recalls308targets but displays195 vs baseline282/197; symbol fusion306/200/full128 is a weak development comparator with interval crossingzero. All seven local/Linux synthetic contracts and607actualQwen baseline replays pass. Separate aggregate availability diagnostic finds363/366current-entity ceiling on exactmapped tasks, not deployable coverage. Frozen7/runtime unchanged. Track only new source/plans/aggregate reports; queue and diagnostic exit0, no training or promotion.

## 2026-10-28 joint-window allocation evidence

Joint7arm and same-score lookahead6arm development experiments complete. Four new global-objective/coherent variants rejected; lookahead384+1visible/+3full is not robust vs matched control. Post-score objective diagnostic records higher-score/lower-coverage association; all failures retained. See R7_JOINT_ALLOCATION_RESULTS.md. Only new research helpers/ops/contracts/plans/aggregate reports and these current-state documents change. Frozen7/runtime unchanged; no confirmation inputs, GPU/model/checkpoint or formal training. Prior head086d7fae17d90a60d283f25b9c6789410642d448 retained; next evidence commit on existing draft PR3 only.

## 2026-10-28 recall and final-window bottleneck evidence

R2six-arm607development experiment improves candidate306->343/366; anchoredpassage24final200->205/full128->134 at256, density+1.30%, finalcoverageCIcrosses0. Label-informed fixed-window diagnostic identifies129fitting but unselected misses;334/366feasibility witness is not achieved or semantic coverage. R1header-order baseline failure retained; R2fixed savedprefix/canonical newquery,7local7Linuxcontracts. No runtime/frozen/confirmation/GPU/training change. See R7_RECALL_WINDOWS_RESULTS.md. Priorcommit671bacbb63c5dcaa8336beb047bcc6dbb9509aa6 retained; reviewedsource/plans/aggregates only, same draftPR3.

## Fixed-pool relevance experiment

## Latest R7: fixed-pool window relevance fusion rejected;384 improves depth at density cost

logs/relevance_windows_r7 exit0:607seen development/366exactmapped/77repos,6actualQwen arms on exact saved passage24(candidate343). Original256 visible205/full-all134/mean250.01/density6.031. New lexical-RRF fusion190/127; original-first-seed anchored fusion196/132. At384 original213/174/mean366.77/density5.106; fused196/163,anchored202/170. Reject all4newarms, no runtime promotion. Original256->384 gains8visible/40full with0loss, mean+46.70%,density-15.34%; exploratory visible repoCI[+0.78,+3.79]pp. Best observed58.20%anyhit and47.54%all-target completeness, not near100%. Full-any/full-all counts coincide here, definitions distinct; no semantic/RL claim.

5local+5Linux contracts,607exactbaselinepayload replays,8actualLandlockdenials/shard,all607x6outputs frozen before labels. Frozen7/runtime unchanged; no newGPU/model/optimizer/training or activejob/monitor. AGGREGATEad286593f0752faeab8c0cd2fa33d7101b4348fa25f43502a017c5999ccf2eb6. See R7_RELEVANCE_WINDOWS_RESULTS.md and RELEVANCE_WINDOWS_R7_REVIEW.json. Next change relevance signal toward issue/code behavior and source dependencies or semantic ranking with predeclared repo-separated validation; stop treating lexical-score increases as coverage evidence. No semantic ranker implemented. R6confirmation excluded; runtime192/128/4096 unchanged.

## Latest R7: structural windows/protection complete; no net task-coverage gain

Two six-arm actualQwen development queues exit0 on607seen inputs/366exactmapped/77repos. Fixed passage24candidate343. Unrestricted structural256 visible200/full129 vs205/134;384211/175 vs213/174,density+3.20%,no coverage gain. Extra structural seeds give same aggregate targetcounts. Source signals occur in552entity-prior/501line-cue inputs out of607; not rare but not validated target relevance.

Follow-up protects original first1or2seeds, sameweights/originalbank. Protect1:200/132at256,211/175at384. Protect2:201/129at256,213/176at384. Protect2/384 totalany213unchanged (7gained7lost),full174->176(10gained8lost),repoCI[-1.90,+3.32]pp crosses0. Targetlines679->707/1320;density5.106->5.379(+5.35%);mean366.77->363.89(-.79%). Keep only exploratory depth/density comparator, not robust coverage/runtime promotion. Bestany remains58.20%;full-all48.09%,not near100%.

10local10Linux firststagecontracts;4local4Linux followupinclprotected3controlidentity.607exactbaseline firststage and607perbudget followup;9/10actualLandlockdenials/shard;alloutputs frozenbeforelabels. One initial syntheticextra-seed fixture failure preserved/repairedbeforedata. Bothqueuescomplete,noactivejob/monitor,newGPU/model/optimizer/training. Frozen7/runtime/R6confirmation unchanged. See R7_BEHAVIOR_WINDOWS_RESULTS.md and bothreviewreports. Aggregate8430ceb24e3bed952ae2358cec2ec8328b89be7bb1a1997dd19b9dae208eb9c5;followup176aa0cc1b0730cc27e161e239cb66bdf604d2283f388fff96d90aedff964514. Next investigate fixed offline semantic relevance with predeclared repo-separated evaluation; no semanticranker implemented and no further per-case heuristic tuning.

## Latest R7: budget/slot study raises final coverage to68.58%, at density cost

Nine actualQwen arms completed607seen development/366exactmapped/77repos, passage24candidate343fixed. Original3slots caps256/384/512/768 give205/213/214/223visible,134/174/191/209full; no-target-entity-selected remains98.6slots at384/512/768 give225/237/251visible,135/171/212full; entitymisses66. Same768cap223→251,+7.65pp repoCI[+4.79,+10.88]pp,35gained7lost; full+3CIcross0. Versus prior384/3,any58.20→68.58%,full47.54→57.92%,butmean366.77→744.86(+103.08%)anddensity5.106→3.179(-37.73%). Keep developmentbreadth/capacity comparators only; no jointdensity/runtimepromotion.

Append original256finalwindows reaches236/166at512,245/180at768,zeroany/fullloss vs256only; lowerdepth/density thanfree6. Best768/6remainingmisses66entityselection+26wrongregion+23candidateabsence. Need better issue/code relevance, not cap-only inflation. Semanticranker notimplemented. Allsource/proposals/scoringfixed;6local6Linuxcontracts,11actualLandlockdenials/shard,607exactpayloadreplaysper256/384. Originalqueueexit1scorerKeyError on nonmappedrows afteralloutputsfreeze; separateeligibilitywrapper4local4Linuxpasses,correctedscore+diagnosticexit0,samegeneration. LocalLinux-resourceimportfailure retained. Frozen7/runtime/confirmationunchanged,noGPU/model/optimizer/training/noactivejobs. SeeR7_CAPACITY_ALLOCATION_RESULTS.md;aggregate68a20273c6b2ef287663382201382b60ad242467b32a1bb607586c06857dbeee.


Track only newcapacitysources/plans/publicreports and the scorer-onlyeligibilityrepair; private frozen generation andscoresstayremote.
