# R7 fixed1024 window location and joint context experiment

No new arm meets the joint coverage+density+completeness objective; keep control1024/8. Control replays272/366any (74.32%),238/366full-all (65.03%),935/1320targetlines,density2.573574,mean998.57tokens. Centered windows yield269any/234full,953targetlines,density2.630562 (+2.21%),mean994.77tokens;3gained6lost any (repo95%CI[-2.55,+0.73]pp),4gained8lost full. More aggregate target lines are not more covered tasks; no promotion.

Joint allocation reduces mean tokens998.57->776.66 (-22.22%) and constructor1.643->0.568s (-65.43%), density+23.43%, butany272->257 (3gained18lost) andfull238->195 (14gained57lost). Combined centered+joint reaches259any/194full,880targetlines,density3.326139 (+29.24%),mean758.24tokens (-24.07%) and0.700s mean (-57.36%). Its any6gained19lost CI[-6.27,-1.20]pp andfull16gained60lost CI[-16.03,-8.14]pp reject it as a replacement. Density improvement partly reflects removing tokens while absolute target-line evidence falls; not a joint improvement.

Cost constraint is not the failure: centered mean+4.56%/P95+6.16%, joint andcombined far faster; all three meet the stated aggregate timing bounds. Entity misses45->45/43 for joint/combined, while wrong-region misses26->41both. The loss concentrates within selected entities. This experiment changes growth policy/granularity/scoring together; it does not prove a single feature causes each loss. Stopping at zero heuristic signal can remove context useful to true targets, so a larger context is not demonstrated waste merely because it lacks query terms.

Bounded follow-up declared from these aggregate findings: preserve joint-selected spans and restore original continuous context growth within the SAME1024cap, compare freshly computed outputs/time. No percase score inspection/tuning, no additional retrieval/model, no runtime promotion. See R7_CONTEXT_REFILL_PLAN.md and eventual R7_CONTEXT_REFILL_RESULTS.md. Both studies remain adaptive reused development, not independent or RL evidence.

## Predeclared arms

All four arms keep1024token ceiling, max8windows and fixed passage24cached candidates. Control exactly replays prior fast1024/8. Centered adds centered3-line windows at the same existing executable anchors and leaves allocation/expansion intact. Joint retains four original-scored seeds, then compares new windows against3-line growth (bounded statement completion up to8addedlines), using existing executable/name-link signals, novelty and rank prior. Combined uses both changes. Joint stops on no positive-signal action, even below budget; at most64actions. Exact Qwen fullpayload costs admit/re-rank every shortlisted action. No new retrieval, neural model or global/cross-snapshot cache. See R7_JOINT_CONTEXT_PLAN.md for full protocol.

The joint treatment changes allocation, growth granularity and its marginal scoring together; it is not a clean isolated causal test of zero-score fill alone. Centered treatment includes original proposals rather than replacing every existing window. Whole original lines and nonoverlap are checked, not semantic or syntactic closure of all windows. Every PI declares partial windows.

## Coverage and density

| Arm | Any /366 | Full-all /366 | Target lines /1320 | Mean tokens /607 | Target lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| control1024_8 | 272 | 238 | 935 | 998.57 | 2.574 |
| centered1024_8 | 269 | 234 | 953 | 994.77 | 2.631 |
| joint1024_8 | 257 | 195 | 859 | 776.66 | 3.177 |
| joint_centered1024_8 | 259 | 194 | 880 | 758.24 | 3.326 |

Budget is a maximum, not minimum. Density is target changed lines per1000actual PI tokens on366mapped tasks; mean tokens are over607generationinputs. Any-hit is at least one target line; full-all is every mapped target line, not semantic sufficiency. Candidate hits stay343/366. Nominal370exact tasks include4unmapped;237other-grade tasks remain outside changed-line denominator.

## Construction time

| Arm | Wall mean / median / P95 (s) | CPU mean (s) | Mean tokenizer misses | Median paired wall ratio |
|---|---:|---:|---:|---:|
| control1024_8 | 1.643 / 1.673 / 2.686 | 1.643 | 1443.7 | 1.000 |
| centered1024_8 | 1.718 / 1.721 / 2.851 | 1.717 | 1557.0 | 1.058 |
| joint1024_8 | 0.568 / 0.511 / 1.116 | 0.568 | 682.5 | 0.336 |
| joint_centered1024_8 | 0.700 / 0.633 / 1.399 | 0.700 | 803.1 | 0.419 |

Each task/arm has a new exact tokenizer cache; armorder rotates within each of4workers. Timing includes source resolution/proposals/constructor but excludes initialretrieval/I/O/imports/tokenizerinit/contracts and Critic. CPU and tokenization counters are in AGGREGATE.json. Compare paired current controls, not absolute timings across previous runs. No measured training wall-time or dynamic/episode integration.

## Paired differences and loss diagnosis

| Arm vs control | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control1024_8 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| centered1024_8 | 3/6 | -0.82 [-2.55,+0.73] | 4/8 | -1.09 [-2.70,+0.62] |
| joint1024_8 | 3/18 | -4.10 [-7.01,-1.93] | 14/57 | -11.75 [-15.70,-7.80] |
| joint_centered1024_8 | 6/19 | -3.55 [-6.27,-1.20] | 16/60 | -12.02 [-16.03,-8.14] |

| Arm | Visible | Candidate absent | Entity not chosen | Chosen entity, wrong region |
|---|---:|---:|---:|---:|
| control1024_8 | 272 | 23 | 45 | 26 |
| centered1024_8 | 269 | 23 | 44 | 30 |
| joint1024_8 | 257 | 23 | 45 | 41 |
| joint_centered1024_8 | 259 | 23 | 43 | 41 |

Repository bootstrap4000resamples seed20261023; exploratory, unadjusted for repeated adaptive development and multiple comparisons.607reused development inputs/366mapped/77repos; no independent acceptance. The loss diagnosis uses labels only after all outputs freeze and does not enter generation. No percase evidence exported, no R6confirmation input.

## Validation and failures

7local+7Linux synthetic contracts pass: exact control identity, centered-originalproposal preservation, caps/roundtrip/nonoverlap/source/no mutation, empty/unstable/unknown, no-relevance underfill, fresh snapshot/repeated calls, Unicode/longlines. ActualQwen607control payloads replay exactly; all607x4payloads checked for exact token budget, original source lines, roundtrip and nonoverlap.

Original logs/joint_context_r7 exit1 BEFORE generation: guard tried a nonexistent fast_memo PRIVATE_SCORED_ROWS file (memo replay has no scorer). Original source/manifest/failure saved in archive/r7_joint_context_missing_score_file, queue retained. Only removed the nonexistent guard;14real label/prior-score path reads denied per shard. The algorithm/arms/plan stayed unchanged. Unique r2queue completes generation/freeze/score/diagnostic exit0.29input SHAmanifest and bash syntax passed.

Windows authority -> reviewed WSLrsync preview/sync -> SHAchecked bash ops/joint_context_r7.sh. Only AGGREGATE,FROZEN,LOSS_DECOMPOSITION downloaded. Private captures/outputs/labels/IDs remain remote. Frozen7/runtime unchanged. No newGPU/model/optimizer/training; no active jobs. Original192/128/4096runtime and disabled start_full97.sh retained. Backup archive/r7_before_joint_context precedes state/doc edits.

AGGREGATE.json SHA e2f683c93b382a11da7b89fbd0d604c1e98b3c83739dc81dbd4d7d993014a447
FROZEN.json SHA ed1b3e5f5c4054277d92fa51433e7f562e1db671169113fc52c1b7a7be800849
LOSS_DECOMPOSITION.json SHA 456105ec397f695f252f984e56ba87667d7e1f9706864a29907f35199605fea1
