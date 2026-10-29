# PI information design: next revision, R6 baseline preserved

User direction on 2026-10-28: prioritize real GPU validation or substantive PI
information design; stop expanding generic launch/dependency checks as the main
research output. Disk was subsequently cleared and the fresh resource check passed.

A direct call to the frozen R6 candidate selector on three new synthetic source
pairs reproduced these candidate-level omissions. No confirmation examples,
labels, model calls, tokenizer coverage or RL measurements were used.

| Synthetic change | Frozen R6 selection | Missing observation |
| --- | --- | --- |
| Add new.py with first(x): return x+1 and second(x): return x-1 | first plus unchanged anchor | second is never offered, despite a free third candidate slot |
| Change module LIMIT=10 to LIMIT=20 above compute(x): return min(x,LIMIT) | compute only | changed constant line lies outside every selected entity |
| Change @cached(10) to @cached(20) above compute | compute only | decorator lies before the selected def-line range |

The causes are precise: dynamic_candidates chooses one smallest entity per diff
interval, so a whole added file collapses into one entity; parse_file indexes only
function/class ranges; function ranges begin at def, excluding decorators. These
are input-representation omissions, not proven historical training bugs or measured
RL regressions. Candidate omission does not quantify final tokenizer-level coverage.

Proposed R7 experiment, kept separate from frozen R6:

1. Assign each changed source span to its smallest enclosing source unit, keeping
   all distinct sibling units before ranking. Do not select one entity for an entire
   multi-entity diff interval. Keep the existing maximum three emitted windows.
2. Extend source units to decorator spans and module-level executable statements
   (assignments/imports). Their exact current-source coordinates and kind must be
   explicit; do not invent a function identity for them or add semantic fix claims.
3. Under the same 128-token update cap, prioritize distinct changed units and their
   minimum coherent context before adding unchanged issue anchors or expanding a
   selected window. Initial 192 and episode 4096 caps remain fixed. Preserve retry,
   causal timing, rollback, unknown/limited and whole-window omission semantics.
4. Measure changed-unit availability, emitted changed lines, per-unit context,
   metadata/token share and useful changes retained before budget exhaustion. Do not
   optimize for emitting more lines indiscriminately. Compare real Qwen-tokenized
   outputs to R6 on synthetic cases and the existing development cohort only.

Run the multi-entity correction separately from module/decorator units so their
benefits and losses can be attributed. Initial candidate recall and caller/callee
context are later hypotheses; do not add them simultaneously without evidence.
Any method change requires its own freeze and genuinely independent confirmation;
the R6 confirmation cohort must not be reused to select or tune R7. R6 stays the
GPU probe baseline. Native training recipe/head/freeze/reward/filter are unchanged.

No R7 runtime implementation, deployment, new coverage claim or model update has
been made. Resource readiness now permits completing the existing disposable GPU
probe path; its remaining launch implementation must be finished without treating
this design note or a resource snapshot as launch approval.

## Development budget/pool evidence after human budget authorization

The six-arm W0 factorial is implemented separately and complete; see R7_BUDGET_RESULTS.md. It is not a deployment of the changed-unit design above. Pool3/256 improves visible171->179 and full105->128 on366 development targets. Pool6 improves candidate242->282 but reduces visible hits at every matched cap. Prioritize candidate-to-window ranking (retrieval prior vs local window utility) rather than simply doubling candidates or budget. Keep module/decorator and multi-unit dynamic corrections separate. No R6 confirmation reuse, no runtime budget change, no transferred GPU/independent-admission claim.

## Window research outcome

Predeclared seven-arm development run is complete (R7_WINDOW_RESEARCH_RESULTS.md). At the same256 cap, ordinal retrieval prior and a same-entity window-repeat penalty improve task coverage179->197 with essentially unchanged mean tokens. The improvement is breadth: full-target only128->130 and target-line density only+0.37%. Rank-prior-only188/full137 gives a more balanced point estimate and+4.93% target-line density, but its coverage CI crosses zero. Whole short-statement proposals and no-expansion compression do not jointly improve objectives. Keep diverse6/rank6 as development comparators; next focus is coherent context retention under cross-candidate diversity. No runtime integration or independent confirmation; module/decorator/dynamic-unit proposal remains separate and unimplemented.

## Candidate retrieval evidence

R7_CANDIDATE_RESEARCH_RESULTS.md records four fixed retrieval hypotheses at unchanged256/max3window allocation. Pool12 raises candidate recall282->308 but final hits197->195. Symbol/signature fusion306candidate/200visible/128full has only+3netvisible and a repo interval crossingzero; no promotion. File diversity and static neighbors do not outperform. Scorer-only current-source/entity ceilings are366/363of366 exact-mapped development tasks, so module/decorator omissions explain only a small part of this W0 subset. This does not negate constructed dynamic omissions. Prioritize joint candidate/window relevance using source-only evidence and coherent context; do not claim more retrieval or shorter code alone improves PI. No confirmation tuning or runtime changes.

## Latest R7: joint budget/window experiments complete; no robust promotion

Two actualQwen development experiments completed exit0 on607inputs/366exactmapped/77repos. Seven-arm joint global-objective beam experiment loses coverage/full/density in all4newarms; symbols12/256 visible200->144,full128->71. Post-score diagnostic shows548/607higher heuristic scores, including62/65lost visible hits: objective misalignment, not proof of individual-feature cause. Diagnostic missing-metric exit1 and CRLFmanifest failure retained, corrected aggregate execution exit0; generation/scoring unchanged.

Six-arm same-score lookahead follow-up preserves original proposals/utility/residual expansion; only selection uses width4 approximate search with greedy incumbent. Base6/256 visible197->195/full130->125; symbols12/256 stays200/128,density+1.29%; symbols12/384 visible208->209/full170->173,density+3.91%, but visible repoCI[-1.03,+1.34]pp and full[-0.29,+2.12]pp include0. No reliable coverage breakthrough. Budget-only original symbols12 256->384 gives200->208visible/128->170full at+46.41%mean tokens and-14.54%density. Retain original comparator; do not deploy new variants.

Fixed symbols12 candidate ceiling306/366=83.61%, observedbest209/366=57.10%(209/306candidate conversion68.30%). Source-union99.18%is an oracle availability ceiling, not token-feasible coverage. Next bounded study: constrained-window budget feasibility diagnostic followed by better relevance calibrated on repository-separated development; labels never enter generation, any new candidate needs fresh independent evidence. No near100claim. See R7_JOINT_ALLOCATION_RESULTS.md and joint/lookahead review+aggregate reports. Joint8local/8Linuxsynthetic contracts,followup4/4;607exactcontrol replay each,6/7Landlockdenials/shard,allgenerationfrozenbeforelabels. Frozen7 rehashed exact; runtime/R6confirmation unchanged. No GPU/model/optimizer/training this round; no jobs or monitor remain.

## Latest R7: candidate recall93.72%; final-window ranking remains main bottleneck

logs/recall_windows_r7_r2 exit0 on607seen development inputs/366exactmapped/77repos, actualQwen6arms. Saved symbols12baseline306candidate/200visible/128full at256. Append-only symbols24 gives327/202/129. Full-body128word passage/stride64 retrieval with3channelRRF and originaltop3anchors gives343/205/134,mean250.01vs249.73tokens,density6.031vs5.954(+1.30%). Candidate37gained0lost,+10.11pp(repoCI[+6.98,+13.29]);final7gained2lost,+1.37pp(repoCI[-0.23,+2.89])notrobust. Unforced-prefix free24 retains343candidate hits but final186/123at256,198/162at384; reject as joint utility improvement. Keep anchored passage24 as next development retrieval comparator, not runtime promotion.

Original60candidate misses:3no parsed target entity;57ranked beyond12 (21at13-24,16at25-48,9at49-96,11at97+ in fixed-prefix canonical expansion).41alreadyhave targetfile amongcandidatefiles,19do not. Post-freeze window diagnostic exit0: passage24/256205visible,23candidateabsent,9no hitting seed,129fitting hitting seed not selected,0standalone-budget-blocked. Label-informed actual-or-single-window witness334/366=91.26%does NOT mean achieved coverage or semantic/fulltarget sufficiency; not globalupperbound. Next priority window relevance with anchors/context, not blanket budget increases. R6confirmation untouched.

R1baseline assertion exit1 retained: oldheaderBM25 set iteration yields floating near-tie ordering; fresh old=new but savedpositions9/10swap. R2preserves savedbaseline/prefix, validates identities/sourcehashes/coordinates, canonicalizes newheaderquery and fixesprocesshashseed. Local7/Linux7contracts inclcrossprocessseeds;607exact256payloadreplays,8actualLandlockdenials/shard;allgenerationfrozenbeforelabels. No prior metrics invalidated/no case-score tuning. See R7_RECALL_WINDOWS_RESULTS.md and RECALL_WINDOWS_R7_REVIEW.json. AggregateSHAc9b4320767e9dfda12e17e53573c0f7f92d155c86f6fd73903e7f508c73b63b6,diagnostic5575bcd833162f8d667e6c965e3b4c22c58e4a569be93b0d00fba9d665926096. Frozen7/runtime unchanged; no newGPU/model/optimizer/training; nojobs/monitorremain.

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
