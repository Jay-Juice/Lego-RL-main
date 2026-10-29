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

## Latest R7: fixed-budget rank and entity allocation completed

No new arm improves final coverage, completeness or density. Reject all four interventions as replacements; retain the exact512/6control (237/366=64.75%any,171/366=46.72%full-all). The previous768/6historical result251/366=68.58% remains the best observed breadth point at higher cost, not a same-budget comparison or new result.

Removing the seed-selection candidate-rank penalty reduces237→182any and171→139full-all,14gained69lost,any delta-15.03pp with exploratory repo95%CI[-19.61,-9.82]pp. Mean tokens506.00→503.85 are nearly unchanged; density3.848→2.942. Combining removal with hard diversity gives the same target counts. The candidate rank prior carries useful information under this scorer; removing it makes no-target-entity misses66→137. This intervention does not prove the prior is optimally calibrated, or isolate which remaining content-score term is weak.

Hard entity diversity raises mean distinct entities5.532→6.000 and lowers no-target-entity misses66→60, but wrong-region misses40→48. Finalany237→235(3gained5lost;repoCI[-2.46,+1.51]pp),full171→164(4gained11lost),density3.848→3.752. Selecting additional entities alone does not ensure the correct lines survive within their windows. Aggregate categories are descriptive; they do not establish that every displaced context caused a particular miss.

Keeping original rank scoring for the first2seeds before flattening later selections reaches208any/150full,13gained42lost,anyCI[-12.83,-2.92]pp; it also fails. This protects seed choices only, not the final context or hits after shared-budget expansion. Do not promote any of these variants or widen the budget to disguise the loss.

Together with the previous budget/slot experiment, the evidence points to a relevance and allocation problem as well as a budget tradeoff: extra budget improves depth, extra slots improve breadth, but indiscriminate diversity or rank flattening hurts. The next distinct research axis is issue-conditioned semantic/behavioral relevance for entity AND within-entity region, retaining the useful retrieval prior and exact source rendering. It should be predeclared and evaluated on repository-separated development before fresh independent confirmation. No semantic reranker is implemented here, and no claim of approaching100% or semantic/RL benefit is supported.

Five512/6arms,607seen development/366exactmapped/77repos,candidate343fixed.7local+7Linuxcontracts,607exactcontrolreplays,12Landlockdenials/shard; alloutputs frozenbeforelabels,score+diagnosticexit0. Frozen7/runtime/R6confirmation unchanged,noGPU/model/optimizer/training/noactivejob. See R7_ENTITY_ALLOCATION_RESULTS.md. AggregateSHA 888113e3970289245208dbdb5c74a93f0929f9b4124332e86ee91b440b9c6e39.

## Latest R7: low-cost allocation and expanded-budget experiment complete

The best practical coverage/depth point in this study is fast1024_8:272/366=74.32%any and238/366=65.03%full-all, versus prior768/6control251/366=68.58% and212/366=57.92%. It gains22any tasks and loses1 (+5.74pp, exploratory repo95%CI[+3.09,+8.43]pp), and gains29full tasks/loses3 (+7.10pp,CI[+4.09,+9.73]pp). Mean construction time1.602→1.645s (+2.70%), median1.575→1.672s (+6.15%), P952.706→2.669s. The paired per-task median time ratio is1.029. This is a coverage improvement with a small mean constructor-time increase relative to the previous768/6development baseline, not proof of equal production training cost.

The tradeoff remains substantial in tokens/density: mean744.86→998.57tokens (+34.06%), visible target lines863→935, but density3.179→2.574target lines/1000PI tokens (-19.05%). Candidate recall stays343/366=93.72%; candidate-to-final conversion reaches272/343=79.30%. Thus more code improves final coverage/depth without a large mean construction penalty, but it is not a joint information-density improvement, near100% result or a deployed1024budget.

At unchanged budgets/window counts, fast512_6 and fast768_6 preserve all measured any/full per-task hit decisions and aggregate target-line/token counts. Mean construction time falls1.323→0.675s (512) and1.602→0.957s (768); medians1.289→0.639s and1.575→0.944s. Mean tokenizer misses2322→880 and2508→1066. The approximate shortlist is empirically adequate on this development cohort; no universal BPE/output-equivalence guarantee follows from equal coverage metrics.

fast768_8 reaches261any/208full with1.179s mean, but versus768/6the any gain10has repoCI[-0.32,+5.69]pp crossing0; full declines4 and density3.179→3.032. Keep only a lower-construction-cost breadth comparator. fast1024_12 also has272any but only214full, density2.368 and2.317s mean. It is worse than1024/8 on aggregate completeness, density and time despite the same any count, so reject12slots as the practical choice. Equal any counts do not imply equal hit sets (27gained6lost vs768control for12slots,22gained1lost for8slots).

Loss diagnosis explains the breadth/depth balance:768/6leaves66no-target-entity and26wrong-region misses;1024/8leaves45and26;1024/12leaves34and37. More slots reach additional entities but spread context thinner.23tasks remain outside the fixed candidate pool in every arm. Retain retrieval prior, moderate breadth and adequate context together; do not keep increasing slots blindly. Source-line integrity is preserved, while semantic completeness remains unproven.

Recommendation is a separate development candidate: fast1024/8for coverage/depth with near-baseline mean constructor time; fast768/6when preserving the prior token/density point and reducing constructor cost is more important. Both require fresh independent confirmation, dynamic/episode integration and actual Critic/training-cost measurement before deployment. Runtime192/128/4096, frozenR6 and training entry stay unchanged. No additional repository search or neural reranker is introduced; initial retrieval cost is excluded rather than claimed free.

Sevenarms607seen/366exactmapped/77repos,candidate343fixed;7local+7Linuxcontracts,607exactcontrols EACH512/768,13Landlockdenials/shard,freeze-before-score/diagnosticexit0. Fresh cache perarm, rotated order; timing is offline constructor only, not live training/Critic overhead. Frozen7/runtime/R6confirmation unchanged,noGPU/model/optimizer/training/noactivejobs. SeeR7_FAST_ALLOCATION_RESULTS.md; aggregateSHA 8454998af70b1666c9f975c4e78a8c2ee88e20b8de53f10547338bc402e4b71f.

### Exact local memoization follow-up

fast768_8 and fast1024_12 each replay all607frozen outputs exactly;4local+4Linuxcontracts,14Landlockdenials/shard,queueexit0. Fixed64metadata-sorted inputs provide paired timings with separate caches/alternating order; see R7_FAST_MEMO_RESULTS.md. No new quality evidence and no silent transfer of these timings to recommended1024/8 (not a memo replay arm). No runtime/GPU/training change. AggregateSHA 5eba17b8a9a459504551601144741e7ef997dd4e89bbb6ebeb37f632a58175ae.

## Latest R7: fixed1024 joint context experiment complete

No new arm meets the joint coverage+density+completeness objective; keep control1024/8. Control replays272/366any (74.32%),238/366full-all (65.03%),935/1320targetlines,density2.573574,mean998.57tokens. Centered windows yield269any/234full,953targetlines,density2.630562 (+2.21%),mean994.77tokens;3gained6lost any (repo95%CI[-2.55,+0.73]pp),4gained8lost full. More aggregate target lines are not more covered tasks; no promotion.

Joint allocation reduces mean tokens998.57->776.66 (-22.22%) and constructor1.643->0.568s (-65.43%), density+23.43%, butany272->257 (3gained18lost) andfull238->195 (14gained57lost). Combined centered+joint reaches259any/194full,880targetlines,density3.326139 (+29.24%),mean758.24tokens (-24.07%) and0.700s mean (-57.36%). Its any6gained19lost CI[-6.27,-1.20]pp andfull16gained60lost CI[-16.03,-8.14]pp reject it as a replacement. Density improvement partly reflects removing tokens while absolute target-line evidence falls; not a joint improvement.

Cost constraint is not the failure: centered mean+4.56%/P95+6.16%, joint andcombined far faster; all three meet the stated aggregate timing bounds. Entity misses45->45/43 for joint/combined, while wrong-region misses26->41both. The loss concentrates within selected entities. This experiment changes growth policy/granularity/scoring together; it does not prove a single feature causes each loss. Stopping at zero heuristic signal can remove context useful to true targets, so a larger context is not demonstrated waste merely because it lacks query terms.

Bounded follow-up declared from these aggregate findings: preserve joint-selected spans and restore original continuous context growth within the SAME1024cap, compare freshly computed outputs/time. No percase score inspection/tuning, no additional retrieval/model, no runtime promotion. See R7_CONTEXT_REFILL_PLAN.md and eventual R7_CONTEXT_REFILL_RESULTS.md. Both studies remain adaptive reused development, not independent or RL evidence.

Fourarms607seen/366mapped/77repos,candidate343fixed;7local7Linuxcontracts,607exactcontrolreplays,14Landlockdenials/shard,29inputSHA,freeze-before-score/diagnosticr2exit0. Originalmissing-memo-score-path guardexit1beforegeneration retained; method unchanged by repair. No newretrieval/GPU/runtime/training/activejobs. SeeR7_JOINT_CONTEXT_RESULTS.md;aggregateSHA e2f683c93b382a11da7b89fbd0d604c1e98b3c83739dc81dbd4d7d993014a447.

## Latest R7: fixed1024 context-refill follow-up complete

Neither follow-up meets the predeclared joint objective. Keep the original fast1024/8 baseline:272/366any (74.32%),238/366full-all (65.03%),935targetlines,density2.573574,mean998.57tokens. The fixed1024budget is not increased and no runtime method is replaced.

Joint+refill reaches267any/229full,931targetlines,density2.555298 (-0.71%),mean1002.02tokens and1.029s mean versus1.643s control (-37.36%). Any3gained8lost CI[-3.54,+0.27]pp;full14gained23lost CI[-5.88,+0.38]pp. It is faster but does not improve coverage or density.

Centered+joint+refill is the better depth/speed comparator:268any/237full,953targetlines,density2.625055 (+2.00%),mean997.33tokens and1.146s mean (-30.22%),median1.034vs1.695,P952.110vs2.665. Any6gained10lost (-1.09pp,repo95%CI[-2.99,+0.86]pp);full17gained18lost (-0.27pp,CI[-3.49,+3.61]pp). More aggregate target lines and density do not satisfy taskcoverage improvement; non-significant negative change is not proof of equivalence/noninferiority. Reject as replacement, retain only developmental cost/depth comparison.

Refill preserves all previously selected joint source intervals and recovers10any/34full from joint257/195, or9any/43full from centeredjoint259/194, without changing candidates/seeds. Thus some context omitted by the zero-positive-signal stopping rule carries true target evidence; low query-match score is not proof of irrelevance. Full restoration does not eliminate remaining placement differences: entitymisses45/43 unchanged and wrongregion41->31/32, compared with control26. Candidateabsence23unchanged. This is evidence about these concrete constructors, not proof that every low-score line is necessary or a universal budget lowerbound.

Across both experiments, no arm raises finaltaskcoverage+density while preservingfulltargets. Stop this bounded allocator study and retain1024/8. No independent/generalization/RL claim, no runtime promotion. Further research would need a more informative issue-to-code relevance signal calibrated separately from this reused cohort, rather than further budget increases, zero-score pruning or blanket window-count changes. No learned ranker was implemented or started this round; no extra online retrieval or neural calls.

Threearms607seen/366mapped/77repos,candidate343fixed;4local4Linuxcontracts,607exactcontrols,607jointspanpreservationeach,15Landlockdenials/shard,35inputSHA,freeze-before-score/diagnosticexit0. Firststage4arms/r2exit0 and originalmissingpathguardexit1 preserved. No newretrieval/GPU/runtime/training/activejobs. SeeR7_CONTEXT_REFILL_RESULTS.md;aggregateSHA baa6b469e9777ea548e040797f7e78e0212610e7a54f9fdcb1101155ad43cbf0.

## Latest R7: historical V2 budget ablation complete

Historical V2 is2048tokens per repair state: code1920 plus execution128, versus current development W0cap1024. The actual repair serializer has these independent limits, so generic/reproduction-shell1024 values are not the effective V2repair cap. This is a budget-only study of currentcodewindows, not a replay of V2information content or its training performance.

Increasing the current fixed8window allocator to1920/2048 improves development coverage without observed any/full regressions. Any272/366(74.32%)->284/366(77.60%) for BOTH larger caps,12gained0lost,+3.28pp, exploratory repo95%CI[+1.53,+5.11]pp. Full-all238/366(65.03%)->266(72.68%) at1920 or270(73.77%) at2048:28/32gained0lost, respectively+7.65ppCI[+4.94,+10.82] and+8.74ppCI[+6.00,+11.78]. Targetlines935->1053/1063. The extra128tokens from1920to2048 add4full tasks in aggregate and10targetlines, with no aggregate any-hit count increase.

Cost fails the predeclared low-construction-overhead criterion. Mean offlineconstructor1.652->3.246/3.445s (+96.51%/+108.54%), median1.689->3.097/3.275, P952.678->6.233/6.830. Meanactualtokens998.57->1741.31/1829.83 (+74.38%/+83.24%). Targetline density2.573574->1.683031/1.619400 (-34.60%/-37.08%). Current1024already uses97.52%of cap onaverage;2048uses89.35%onaverage andmedian2039tokens. Largerbudget improves absolute target evidence and completeness, but not informationdensity or cheapconstruction. No extra retrieval/modelcalls were added; more repeated exacttokenization/contextgrowth increases constructorwork. ProductionCritic/trainingcost remains unmeasured.

Loss categories show why the gain saturates: candidateabsence23and no-target-entity-selected45 unchanged; selected-entity/wrong-region26->14 at bothlargercaps. Thus additionalcontext resolves12of26within-entity misses, while68misses remain in candidate/selection stages. Candidate343/366=93.72%unchanged. This directly supports a budget contribution and a separate entity-selection bottleneck; it does not prove a universal cap or an achievable100% result.

Keep1024/8as current practical baseline under the user's lowlatency/density preference. Retain1920/2048only as higher-completeness development comparators; do not deploy automatically. Any future largerbudget use first needs cheaper equivalent construction and better entity/windowrelevance, followed by freshindependent/dynamic/episode/Criticcost validation. This study is607reuseddevelopment inputs/366mapped/77repos, not independentgeneralization orRLbenefit. RuntimeR6 remains192/128/4096 and trainingdisabled.

Three arms607seen/366mapped/77repos,candidate343fixed;7local7Linuxcontracts,607exactcontrols,16Landlockdenials/shard,29inputSHA,freeze-before-score/diagnosticexit0. No newretrieval/GPU/runtime/training/activejobs. SeeR7_V2_BUDGET_RESULTS.md;aggregateSHA 3a01ffe435736374dc849940bb724be05a7a74193f28e1a9c971bc5bd3defcea.

## Latest R7: entity selection and exact construction optimization complete

This bounded experiment achieves an exact construction-cost reduction, but neither new entity-selection rule meets the joint coverage/density/completeness objective. Retain the original1024/8 selection and the new cached1024_8 development implementation; reject entity1024_8 and complement1024_8 as replacements. No runtime promotion or training change.

The cached arm exactly replays all607 complete baseline output dictionaries, including tokens/source maps/windows/semantic hashes. Any-hit remains272/366(74.32%), full-all238/366(65.03%), visible targetlines935/1320, density2.573574targetlines/1000PI tokens, mean998.57tokens. Mean construction time1.643644->1.320374s (-19.67%), median1.699404->1.366917s, P952.683700->2.123874s (-20.86%); median paired time ratio0.8139. Mean unique tokenizer misses remain1443.66 in both arms; the optimized arm averages90.11 backend batches. The combined AST/line/term cache and batch optimization is measured together, not proof that batching alone caused the gain or that fewer source strings were tokenized. No persistent cache or additional retrieval/modelcall.

Whole-unit evidence weighting reaches268any(73.22%)/236full(64.48%),953targetlines,density2.634249 (+2.36%),996.51mean tokens,1.329902s mean. It gains3andloses7any tasks (-1.09pp, exploratory repo95%CI[-2.81,+0.59]pp), gains4andloses6full (-0.55pp,CI[-2.24,+1.21]). Complementary evidence reaches267any(72.95%)/235full(64.21%),951targetlines,density2.627239 (+2.09%),996.75tokens,1.328945s mean;3gained8lost any (-1.37pp,CI[-3.16,+0.34]),4gained7lost full (-0.82pp,CI[-2.66,+1.02]). Both are faster than original control because they share the exact performance changes; neither improves task coverage or completeness. Intervals crossing0 are not evidence of equivalence/noninferiority.

The loss diagnosis rejects the intended selection improvement: no-target-entity-selected45->55/56, while within-selected-entity wrong-region misses26->20; candidateabsence23unchanged. More aggregate targetlines and slightly higher density do not compensate for fewer covered tasks. Candidate-own lexical/identifier evidence with the fixed bounded multiplier is insufficient in this form; this experiment does not establish that all entity-level signals are useless. Preserve the useful rank prior and original choices rather than deploy these weights.

Keep budget1024 and original quality; use the proven exact cached/batched constructor as the next W0 development control. Any future selection research needs a more discriminating issue-to-code relevance signal evaluated on repository-separated development and fresh independent evidence; no learned model or additional parameter sweep was started. All607cases are reused development (366mapped/77repos); no independent generalization, semantic completeness or RL claim. Timing excludes initial retrieval/I/O/init/Critic; the20% constructor improvement is not a20% training speedup. FrozenR6 runtime192/128/4096 and disabled training entry remain unchanged.

Four arms607seen/366mapped/77repos,candidate343fixed;8local8Linuxcontracts,607exactcontrols+cachedreplays,17Landlockdenials/shard,29inputSHA,freeze-before-score/diagnosticexit0. No newretrieval/GPU/runtime/training/activejobs. SeeR7_ENTITY_EVIDENCE_RESULTS.md;aggregateSHA e3cb8c71350dd73b83cec005082889e889d370fe0f40a82d56957df61c55b8da.

## Latest R7: scope-local window experiment complete

Neither scope-local arm meets the joint objective. Retain cached1024/8 original selection; reject scope1024_8 and balanced1024_8 as replacements. No runtime promotion. The class-scope hypothesis was tested rather than assumed: more syntactically localized proposals do not improve relevance selection in this implementation.

Baseline272/366any(74.32%),238full-all(65.03%),935targetlines,998.57mean tokens,density2.573574,meanconstructor1.330030s/P952.148445s. Scope-local243any(66.39%)/221full(60.38%),898targetlines,935.36tokens,density2.688542,mean1.070609s/P951.988183s. It gains8andloses37any (-7.92pp, exploratory repo95%CI[-11.18,-5.00]pp), gains17andloses34full (-4.64pp,CI[-7.95,-1.12]). Balanced241any(65.85%)/219full(59.84%),887targetlines,933.93tokens,density2.661130,mean1.068976s/P951.966204s;7gained38lostany (-8.47pp,CI[-11.60,-5.54]),16gained35lostfull (-5.19pp,CI[-8.62,-1.56]). Both pass timing bounds and raise density by using fewer tokens, but lose absolute targetlines/taskcoverage/completeness. These are rejected tradeoffs, not coverage improvements.

The new post-freeze diagnostic directly identifies a more specific bottleneck. Of366tasks,343have a target-containing candidate interval;333(90.98%ofalltasks) already have at least one actual target-containing seed window that individually fits1024. Baseline94misses partition into23candidateabsence,7no-target-seed,64feasible-target-seed-not-emitted;0are solely targetseed-overbudget. Thus64/94=68.09%ofbaseline missedtasks already had an individually feasible correct source window. This is stronger evidence about ranking/combination loss than simply quoting candidate recall. It does NOT show that every target can jointly fit1024, establish achievable91%coverage without labels, or explain full-all completeness by itself. Three baseline hits arise through context growth despite no target-containing seed, so333-272 is not the64miss count.

Scope-local has330individuallyfeasibletargetseedtasks but only243visible; balanced has335feasibletargetseedtasks (more thanbaseline333) yet241visible. Feasible-seed-not-emitted misses rise64->88/95; no-target-seedmisses7->12/7. Merely increasing proposal breadth or changing ownership boundaries is insufficient.362/366tasks have at leastoneclasscandidate, so the4task no-class stratum is too small for broad subgroup conclusions. These compound policies alter seed signals/cap selection/repetition and expansion boundaries; results do not isolate a single cause. Class-range recall can be broad, but in this cohort most candidate-hit tasks already contain small feasible seeds, so class granularity alone does not account for the gap.

Keep1024budget and existing exactcached constructor. This bounded study is complete; do not sweep its parameters on the same cohort. A stronger issue-to-window relevance model with repository-separated development is a plausible future direction, not a demonstrated improvement or an implemented/approved learned ranker. Offline training and small online scoring could be evaluated for latency, but no extra model/dependency/download/training is introduced here. No near100%claim. All607inputs are reuseddevelopment; R6independentconfirmation untouched. Candidate recall343/366unchanged; frozenR6/runtime192/128/4096 and disabledformaltraining remain unchanged.

Three arms607development/366mapped77repos;8local8Linuxcontracts;607exactcontrol;18Landlockdenials;35inputSHA;freeze-before-score and queueexit0. Runtime/frozenR6unchanged,noactivejob. See R7_SCOPE_WINDOWS_RESULTS.md; aggregateSHA 02f815c93faabb058f0b576ab5b7814bcb8c769a240ac35f4adacf3102e08d60.
