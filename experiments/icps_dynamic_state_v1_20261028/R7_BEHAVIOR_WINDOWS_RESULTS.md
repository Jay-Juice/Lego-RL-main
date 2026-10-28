# R7 issue/AST window research and protected follow-up

Two six-arm actualQwen development experiments completed exit0. No net task-coverage improvement. The best follow-up protects the original first2seeds at384: any-hit213unchanged (7gained/7lost), full-all174→176 (10gained/8lost), target lines679→707 of1320, density5.106→5.379(+5.35%), mean tokens366.77→363.89(-0.79%). Keep only as exploratory depth/density comparator, not a coverage winner or runtime promotion. Full-all repo95%CI[-1.90,+3.32]pp crosses0; no robust completeness claim. Target-line coverage51.44%→53.56% is a different metric from task-any58.20%.

## First experiment: issue-explicit and AST signals

Fixed saved passage24 candidate recall343/366; current-source windows ranked using explicit issue identifiers/calls/traceback frame names, exact literal error messages, weak named-entity and unique one-hop callee priors, nearest preceding local stores, enclosing if guards and linked returns. Original score scale and exact marginal cost retained. Extension arm additionally proposes3/5/7line windows at top6structural anchors/entity; all old proposals retained. No execution, learned weights or labels in generation.

| Arm | Any task /366 | All target lines /366 | Mean tokens /607 | Target lines /1000PI tokens |
|---|---:|---:|---:|---:|
| base256 | 205 | 134 | 250.01 | 6.031 |
| base384 | 213 | 174 | 366.77 | 5.106 |
| rank256 | 200 | 129 | 249.66 | 5.892 |
| rank384 | 211 | 175 | 363.62 | 5.269 |
| extend256 | 200 | 129 | 249.66 | 5.892 |
| extend384 | 211 | 175 | 363.62 | 5.269 |

Unrestricted256 loses5any/full;384 loses2any, gains1full and3.20%density. These are not a joint coverage/completeness improvement. Extension has the same aggregate target counts as reweighting alone; that does not imply identical payloads. Source-only mechanisms occur on many of607inputs:552entity-prior,501line-cue,469explicit-call,356nearest-store,300linked-return,274one-hop-callee,206enclosing-guard,94literal-message. Counts describe signal availability, not correct targets or measured causal contributions. No claim that all structural approaches fail.

## Follow-up: reserve original first1or2seeds

Adaptive experiment predeclared after aggregate-only first results; no individual scores inspected. Same structural weights, same candidate pool, original seed bank and allocator; structural adjustment applies only after the protected count. Original context expansion still shares the budget, so protecting seeds does not preserve every final source range or task hit. No added seeds in this follow-up.

| Arm | Any task /366 | All target lines /366 | Mean tokens /607 | Target lines /1000PI tokens |
|---|---:|---:|---:|---:|
| base256 | 205 | 134 | 250.01 | 6.031 |
| base384 | 213 | 174 | 366.77 | 5.106 |
| protect1_256 | 200 | 132 | 249.67 | 5.815 |
| protect1_384 | 211 | 175 | 364.24 | 5.212 |
| protect2_256 | 201 | 129 | 249.52 | 5.952 |
| protect2_384 | 213 | 176 | 363.89 | 5.379 |

Protect1fails to improve task coverage at either budget. Protect2/256 still loses4any and5full. Protect2/384 preserves only the total any-hit count, not the task set; any repoCI[-2.05,+2.41]pp. Full-all gain2is uncertain. All intervals are exploratory unadjusted reused-development estimates, not evidence for a selected winner after repeated search. No statistical interval is claimed for the descriptive5.35%density increase.

## Interpretation and next research boundary

This pair of experiments does not raise best observed any-task coverage above213/366=58.20%. Full-all reaches176/366=48.09% versus47.54% at the same384cap. Candidate recall remains343/366=93.72%. The remaining bottleneck cannot be resolved by declaring all observed call/name relations relevant. Next bounded study should test a different relevance signal, such as offline issue-to-code semantic judging with a fixed local model and predeclared prompts/candidate context, alongside repository-separated evaluation. This is a proposed next method, not an implemented or validated semantic reranker. No further hand-tuning on individual development or R6confirmation targets.

Density is visible target-coordinate evidence per1000actualPI tokens; full-all means every mapped target changed line, not complete function/control-flow understanding or RL benefit. Prior oracle union/single-seed witnesses are not attainable deployed accuracy. No100%promise. Frozen R6/runtime stays192/128/4096 and formal start_full97.sh remains disabled.

## Validation and retained history

First stage10local+10Linux synthetic contracts,9actualLandlockdenials/shard,607exact prior256payload replays. Follow-up4local+4Linux contracts (including protected3exact original control),10actualdenials/shard,607exact payload replays for EACH256/384control. Four shards, all607x6outputs frozen before scoring perstage. ActualQwen roundtrip/cap/max3/nonoverlap/source-line checks pass. Both queues exit0/state complete_development_only; no active jobs/monitor. Frozen7/runtime unchanged; no GPU/model/optimizer/training this turn. Only public aggregates/freeze receipts downloaded; private inputs/IDs/scores remain remote.

First local extra-seed test initially failed because the synthetic fixture was already covered by old seeds (9pass1fail); fixture strengthened before any data execution, final10pass. Original source and failure retained at archive/r7_behavior_synthetic_fixture_failure. No development-label-driven repair. Prior negative methods retained.

Windows source authority -> reviewed WSLrsync preview/sync/SHA -> bash ops/behavior_windows_r7.sh and ops/protected_behavior_r7.sh.607previously seen tasks,366exactmapped/77repos;370nominal exact labels include4unmapped,237remaining inputs have other label grades. Rates are conditional on366, not all607/new repositories. R6independent confirmation untouched.

First AGGREGATE SHA: 8430ceb24e3bed952ae2358cec2ec8328b89be7bb1a1997dd19b9dae208eb9c5
Follow-up AGGREGATE SHA: 176aa0cc1b0730cc27e161e239cb66bdf604d2283f388fff96d90aedff964514
