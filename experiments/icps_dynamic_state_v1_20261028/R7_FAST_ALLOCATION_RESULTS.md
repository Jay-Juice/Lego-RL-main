# R7 low-cost window allocation and budget study

Candidate recall and final coverage are different stages: the fixed candidate pool contains a target in343/366tasks (93.72%); the previous final768/6PI contains one in251/366 (68.58%). This study changes final selection cost and budget, not candidate retrieval. It uses cached source candidates, no new repository search, neural model, or downloads.

The best practical coverage/depth point in this study is fast1024_8:272/366=74.32%any and238/366=65.03%full-all, versus prior768/6control251/366=68.58% and212/366=57.92%. It gains22any tasks and loses1 (+5.74pp, exploratory repo95%CI[+3.09,+8.43]pp), and gains29full tasks/loses3 (+7.10pp,CI[+4.09,+9.73]pp). Mean construction time1.602→1.645s (+2.70%), median1.575→1.672s (+6.15%), P952.706→2.669s. The paired per-task median time ratio is1.029. This is a coverage improvement with a small mean constructor-time increase relative to the previous768/6development baseline, not proof of equal production training cost.

The tradeoff remains substantial in tokens/density: mean744.86→998.57tokens (+34.06%), visible target lines863→935, but density3.179→2.574target lines/1000PI tokens (-19.05%). Candidate recall stays343/366=93.72%; candidate-to-final conversion reaches272/343=79.30%. Thus more code improves final coverage/depth without a large mean construction penalty, but it is not a joint information-density improvement, near100% result or a deployed1024budget.

At unchanged budgets/window counts, fast512_6 and fast768_6 preserve all measured any/full per-task hit decisions and aggregate target-line/token counts. Mean construction time falls1.323→0.675s (512) and1.602→0.957s (768); medians1.289→0.639s and1.575→0.944s. Mean tokenizer misses2322→880 and2508→1066. The approximate shortlist is empirically adequate on this development cohort; no universal BPE/output-equivalence guarantee follows from equal coverage metrics.

fast768_8 reaches261any/208full with1.179s mean, but versus768/6the any gain10has repoCI[-0.32,+5.69]pp crossing0; full declines4 and density3.179→3.032. Keep only a lower-construction-cost breadth comparator. fast1024_12 also has272any but only214full, density2.368 and2.317s mean. It is worse than1024/8 on aggregate completeness, density and time despite the same any count, so reject12slots as the practical choice. Equal any counts do not imply equal hit sets (27gained6lost vs768control for12slots,22gained1lost for8slots).

Loss diagnosis explains the breadth/depth balance:768/6leaves66no-target-entity and26wrong-region misses;1024/8leaves45and26;1024/12leaves34and37. More slots reach additional entities but spread context thinner.23tasks remain outside the fixed candidate pool in every arm. Retain retrieval prior, moderate breadth and adequate context together; do not keep increasing slots blindly. Source-line integrity is preserved, while semantic completeness remains unproven.

Recommendation is a separate development candidate: fast1024/8for coverage/depth with near-baseline mean constructor time; fast768/6when preserving the prior token/density point and reducing constructor cost is more important. Both require fresh independent confirmation, dynamic/episode integration and actual Critic/training-cost measurement before deployment. Runtime192/128/4096, frozenR6 and training entry stay unchanged. No additional repository search or neural reranker is introduced; initial retrieval cost is excluded rather than claimed free.

## All predeclared quality results

| Arm | Any /366 | Full-all /366 | Mean tokens /607 | Target lines /1320 | Lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| control512_6 | 237 | 171 | 506.00 | 712 | 3.848 |
| control768_6 | 251 | 212 | 744.86 | 863 | 3.179 |
| fast512_6 | 237 | 171 | 506.00 | 712 | 3.848 |
| fast768_6 | 251 | 212 | 744.86 | 863 | 3.179 |
| fast768_8 | 261 | 208 | 758.05 | 839 | 3.032 |
| fast1024_8 | 272 | 238 | 998.57 | 935 | 2.574 |
| fast1024_12 | 272 | 214 | 1016.36 | 880 | 2.368 |

The allocator retains the existing proposal bank, rank prior, lexical novelty/repetition score and exact source renderer. It approximates marginal token cost using independently tokenized window bodies to shortlist8choices per slot, then uses exact full-payload costs and original utility among feasible shortlisted choices. If none fits, it tries the next8. Every chosen seed, context expansion and final payload is checked with the actual tokenizer. Approximate token costs never authorize overflow; this is nevertheless approximate selection and not guaranteed to reproduce every control output under BPE. Context expansion is unchanged.

## Independently cached construction timing

| Arm | Wall mean / median / P95 (s) | CPU mean (s) | Mean tokenizer misses | Mean bytes tokenized | Median paired wall ratio |
|---|---:|---:|---:|---:|---:|
| control512_6 | 1.323 / 1.289 / 2.233 | 1.323 | 2322.0 | 1646097 | 1.000 |
| control768_6 | 1.602 / 1.575 / 2.706 | 1.601 | 2508.0 | 2141252 | 1.000 |
| fast512_6 | 0.675 / 0.639 / 1.207 | 0.675 | 879.5 | 562901 | 0.502 |
| fast768_6 | 0.957 / 0.944 / 1.613 | 0.957 | 1065.5 | 1058056 | 0.597 |
| fast768_8 | 1.179 / 1.171 / 1.888 | 1.179 | 1213.6 | 1400744 | 0.746 |
| fast1024_8 | 1.645 / 1.672 / 2.669 | 1.645 | 1443.7 | 2257007 | 1.029 |
| fast1024_12 | 2.317 / 2.380 / 3.617 | 2.317 | 1773.8 | 3381943 | 1.464 |

Each arm has a fresh exact tokenizer cache per task; no cross-arm reuse. Execution order rotates over the seven arms by source-only global row position. Measurements include the serializer, source resolution/proposal generation and final construction; exclude file I/O, initial retrieval, imports/tokenizer initialization, external contract checks and downstream Critic work. Warm compiled-function reuse is part of the fast implementation. Four concurrent CPU workers and warm system/tokenizer effects remain; these are offline constructor measurements, not end-to-end training latency. No added retrieval calls by design is distinct from a measured bound on total training overhead. No episode/update-cache integration is tested.

Tokenizer misses and encoded bytes quantify repeated full-prefix work; wall and CPU times are reported separately. Median paired ratios use512control for512arms and768control for768/1024arms. Comparing1024to768 changes output cost as well as algorithm; it is not a same-budget speedup.1024is33%above768but over5x frozen192W0, so it is an experimental cap, not a deployed default.

## Paired quality and aggregate diagnosis

| Arm versus stated control | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control512_6 vs control512_6 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| control768_6 vs control768_6 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| fast512_6 vs control512_6 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| fast768_6 vs control768_6 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| fast768_8 vs control768_6 | 17/7 | +2.73 [-0.32,+5.69] | 14/18 | -1.09 [-4.98,+2.23] |
| fast1024_8 vs control768_6 | 22/1 | +5.74 [+3.09,+8.43] | 29/3 | +7.10 [+4.09,+9.73] |
| fast1024_12 vs control768_6 | 27/6 | +5.74 [+2.50,+9.31] | 24/22 | +0.55 [-3.63,+3.99] |

| Arm | Visible | Candidate absent | No target entity chosen | Target entity chosen, wrong region |
|---|---:|---:|---:|---:|
| control512_6 | 237 | 23 | 66 | 40 |
| control768_6 | 251 | 23 | 66 | 26 |
| fast512_6 | 237 | 23 | 66 | 40 |
| fast768_6 | 251 | 23 | 66 | 26 |
| fast768_8 | 261 | 23 | 45 | 37 |
| fast1024_8 | 272 | 23 | 45 | 26 |
| fast1024_12 | 272 | 23 | 34 | 37 |

All confidence intervals are exploratory4000-resample repository bootstrap (seed20261023), unadjusted for repeated adaptive development and multiple comparisons.607previously seen development inputs;366exactmapped tasks/77repos in changed-line coverage.370nominal exact-label tasks include4unmapped;237other-grade tasks are outside that denominator. Any-hit means at least one target changed line; full-all means all target changed lines, not semantic sufficiency. Density is target-line evidence per actual PI tokens on366tasks, not RL information gain. Post-freeze loss categories do not feed generation. Private cases and labels remain remote; R6confirmation is excluded.

## Validation and runtime limits

Seven local and seven Linux synthetic contracts passed, including additive-tokenizer exact controls, independent cache counters, exact-cost admission when estimates disagree, shortlist fallback, Unicode/single-entity cases, caps/source/nonoverlap and explicit empty state. Two exact previous Qwen control payloads replayed for every607input. Seven arms use actual Qwen cap/roundtrip/full-source-line/nonoverlap checks. Whole source lines do not guarantee complete semantic/control-flow units.

Four source-only Landlock workers each denied13label/prior-score paths. All607x7outputs frozen before separate scoring and aggregate loss diagnostic; queue exit0.23inputSHAmanifest and shell syntax pass. Windows backup archive/r7_before_fast_allocation precedes document edits. Windows authority -> reviewed WSLrsync preview/sync/SHA -> bash ops/fast_allocation_r7.sh. Only these3aggregate/freeze reports downloaded.

Frozen7/runtime unchanged. No GPU/model/optimizer/training launched this round; no active job remains. Runtime192/128/4096 and formal start_full97.sh exit78 remain. Increasing W0 while keeping episode4096 reduces future update capacity; a larger PI also increases Critic sequence work. Both need separate end-to-end evaluation before adoption. No blanket no-overhead claim or independent admission.

AGGREGATE.json SHA 8454998af70b1666c9f975c4e78a8c2ee88e20b8de53f10547338bc402e4b71f
FROZEN.json SHA 88641985551f5f05c68cca51c0b3a1160c719512c84c8bea0583da7ccf4bf42e
LOSS_DECOMPOSITION.json SHA a72df8b2bd6750999bcb6d6a8b3f327e02984a1651102875e0e28ef7d99d5baf
