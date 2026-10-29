# R7 actual-window joint budget allocation: two completed development experiments

## Decision

No robust joint improvement in task coverage, target completeness and information-density proxy. Keep the existing diverse6 development comparator; do not promote these prototypes or change frozen R6/runtime. The best observed task coverage is209/366(57.10%) at cap384, only1case above its matching old-search control208/366. This is not evidence of approaching100%.

## Scope and metrics

607 previously seen development tasks,366 exactmapped target tasks across77repositories. Actual local Qwen tokenizer, same cached source and candidate pools; at most3actual contiguous code windows. W0 caps256/384 are authorized experimental settings; frozen deployment remains192/128/4096. All generation is completed and hashed before scoring, with actual Landlock label/previous-score denials. No R6 confirmation access, GPU/model/optimizer update, runtime deployment or formal training this round.

Candidate hit means a target intersects the candidate source entity. Visible hit means target source lines actually enter final PI. Full means the scorer's full-target coordinate coverage, not independently verified semantic sufficiency. Density is visible target source lines per1000 PI tokens on the same366cases; mean token cost uses all607cases. These are evidence-location proxies, not RL reward or mutual information. Exploratory repo intervals are unadjusted and reuse development data.

## First experiment: global objective plus joint allocation

New objective combines issue-term coverage, repetition discount, source-line relevance and rank prior; width8 approximate beam selects at most3nonoverlapping windows under actual rendered token cost, then expands context. Coherent variants additionally offer bounded short-statement closure and complete small entities. Because objective, proposal/pruning and search changed together, failure does not isolate any one feature.

| Arm | Cap | Candidate hit | Visible hit | Full | Mean tokens | Target lines/1000 tokens |
|---|---:|---:|---:|---:|---:|---:|
| base6_256 | 256 | 282 | 197 | 130 | 249.76 | 5.867 |
| base12_256 | 256 | 306 | 200 | 128 | 249.73 | 5.954 |
| base12_384 | 384 | 306 | 208 | 170 | 365.63 | 5.089 |
| joint6_256 | 256 | 282 | 161 | 80 | 251.98 | 4.696 |
| joint12_256 | 256 | 306 | 144 | 71 | 253.42 | 4.092 |
| coherent12_256 | 256 | 306 | 147 | 77 | 251.46 | 4.525 |
| coherent12_384 | 384 | 306 | 166 | 109 | 374.63 | 3.671 |

All four new arms lose visible coverage, completeness and density against their matching candidate/budget controls. Visible repo intervals lie entirely below0. Reject these implementations. Adding syntax closure did not compensate for the changed selection objective.

## Follow-up: preserve original scoring, replace only greedy selection

Declared after seeing the first experiment's aggregate failure, without per-case inspection. Original diverse6 proposals, marginal utility, rank/diversity penalties and residual expansion remain identical. Fixed width4 lookahead replaces only the greedy selection loop, retains the original greedy incumbent and uses actual combined rendered token cost. This is approximate search, not guaranteed optimality. Six separately frozen arms:

| Arm | Cap | Candidate hit | Visible hit | Full | Mean tokens | Target lines/1000 tokens |
|---|---:|---:|---:|---:|---:|---:|
| base6_256 | 256 | 282 | 197 | 130 | 249.76 | 5.867 |
| base12_256 | 256 | 306 | 200 | 128 | 249.73 | 5.954 |
| base12_384 | 384 | 306 | 208 | 170 | 365.63 | 5.089 |
| lookahead6_256 | 256 | 282 | 195 | 125 | 249.79 | 5.924 |
| lookahead12_256 | 256 | 306 | 200 | 128 | 249.45 | 6.031 |
| lookahead12_384 | 384 | 306 | 209 | 173 | 365.02 | 5.288 |

At symbols12/256, visible/full are unchanged200/128; density5.954→6.031(+1.29%). At symbols12/384, visible208→209(+0.27pp;3gained/2lost),full170→173; density5.089→5.288(+3.91%). The matching visible repo95%interval[-1.03,+1.34]pp and full interval[-0.29,+2.12]pp both include0. Keep as an exploratory comparator, not a robust improvement. Base6/256 loses2visible/5full.

Budget-only old symbols12 allocation256→384 increases average tokens249.73→365.63(+46.41%),visible200→208(+2.19pp),full128→170,while density5.954→5.089(-14.54%). The budget increase mostly buys completeness and is not a density-preserving breakthrough. This comparison is arithmetic on the same arms; aggregate default base6 intervals must not be misreported as budget-only confidence intervals.

## Post-score objective diagnostic

The joint12_256 heuristic rises on548/607tasks. Of its65lost visible hits,62have a higher new objective; only8of9gained hits occur with higher objective. This confirms an observed score/coverage mismatch rather than insufficient optimization of that score. It does not identify which feature caused the loss. Diagnostic includes only366evaluable rows for score-vs-hit counts, explicitly excludes241unavailable rows, and reproduces paired gain/loss totals. It never modifies the selector or reads confirmation cases. See reports/joint_windows_r7/OBJECTIVE_DIAGNOSTIC.json, SHAeca83516254a31e15c1b02753736193fcddb37b23abdbe3567e7d3a7726848b8.

## What this says about100%

With the fixed symbols12 candidate set, only306/366cases contain any target. Thus even a perfect selector limited to those candidates cannot exceed83.61%task-hit coverage on this subset. The current best209/306=68.30%candidate-to-PI conversion leaves97candidate-containing cases unexposed, plus60cases missing at candidate retrieval. More search did little under the existing relevance signal. Increasing tokens helps completeness but also spends tokens on irrelevant context.

Previous source-union oracle363/366=99.18%only says a target exists somewhere in parsed source entities. It ignores candidate selection, limited windows, token caps and semantic completeness; it is not an achievable operating point or an independent-data estimate. No method here warrants80%,90%or100%claims.

Next bounded research should distinguish representation/budget feasibility from relevance ranking before another heuristic sweep: scorer-only constrained-oracle diagnostics over fixed admissible windows at real token costs; then candidate/window relevance learned or calibrated solely on separated development repositories, with intact source-statement context and incremental-information penalty. Oracle labels must never enter the deployed selector. Any learned or revised selector needs a fresh freeze and untouched independent evaluation; no R6 confirmation tuning. This is a proposed next experiment, not implemented or validated here.

## Evidence and retained failures

Joint queue logs/joint_windows_r7 exit0:8local+8Linuxsynthetic contracts,607baseline exact replays,6Landlockdenials/shard. Lookahead logs/lookahead_windows_r7 exit0:4newlocal+4Linuxcontracts,607baseline exact,7denials/shard. Shared controls agree across rounds. All per-case inputs, generated PI and scores remain remote; only aggregate reports exported. No code-source or labels are exported here.

Initial joint synthetic full-entity retention failure was fixed before generation and archived. Explicit UTF8 repaired a local preparation decode failure. Post-score diagnostic first failed on missing exact-target fields for non-evaluable rows; fixed by explicit exclusion and366evaluable assertions, with initial source/logs retained. A CRLF checksum-manifest transport failure was retained and LF normalization applied; neither changed generation/scoring.

See reports/JOINT_WINDOWS_R7_REVIEW.json, LOOKAHEAD_WINDOWS_R7_REVIEW.json, joint_windows_r7/AGGREGATE.json and lookahead_windows_r7/AGGREGATE.json. Full generation receipts and aggregate SHA values remain in the reviews and FROZEN files. No monitors or jobs remain after completion.
