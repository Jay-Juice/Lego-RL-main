# R7 fixed-budget entity allocation

Five predeclared arms, all512token/max6windows and the same saved passage24 candidates (343/366=93.72%). Source proposals, rendering, costs and context expansion are unchanged. This isolates the seed-selection candidate-rank penalty and repeated-entity preference. It does not introduce a semantic model or learn weights from case scores.

No new arm improves final coverage, completeness or density. Reject all four interventions as replacements; retain the exact512/6control (237/366=64.75%any,171/366=46.72%full-all). The previous768/6historical result251/366=68.58% remains the best observed breadth point at higher cost, not a same-budget comparison or new result.

Removing the seed-selection candidate-rank penalty reduces237→182any and171→139full-all,14gained69lost,any delta-15.03pp with exploratory repo95%CI[-19.61,-9.82]pp. Mean tokens506.00→503.85 are nearly unchanged; density3.848→2.942. Combining removal with hard diversity gives the same target counts. The candidate rank prior carries useful information under this scorer; removing it makes no-target-entity misses66→137. This intervention does not prove the prior is optimally calibrated, or isolate which remaining content-score term is weak.

Hard entity diversity raises mean distinct entities5.532→6.000 and lowers no-target-entity misses66→60, but wrong-region misses40→48. Finalany237→235(3gained5lost;repoCI[-2.46,+1.51]pp),full171→164(4gained11lost),density3.848→3.752. Selecting additional entities alone does not ensure the correct lines survive within their windows. Aggregate categories are descriptive; they do not establish that every displaced context caused a particular miss.

Keeping original rank scoring for the first2seeds before flattening later selections reaches208any/150full,13gained42lost,anyCI[-12.83,-2.92]pp; it also fails. This protects seed choices only, not the final context or hits after shared-budget expansion. Do not promote any of these variants or widen the budget to disguise the loss.

Together with the previous budget/slot experiment, the evidence points to a relevance and allocation problem as well as a budget tradeoff: extra budget improves depth, extra slots improve breadth, but indiscriminate diversity or rank flattening hurts. The next distinct research axis is issue-conditioned semantic/behavioral relevance for entity AND within-entity region, retaining the useful retrieval prior and exact source rendering. It should be predeclared and evaluated on repository-separated development before fresh independent confirmation. No semantic reranker is implemented here, and no claim of approaching100% or semantic/RL benefit is supported.

## Every predeclared arm

| Arm | Any /366 | Full-all /366 | Mean tokens /607 | Mean entities /607 | Target lines /1320 | Lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|---:|
| control512 | 237 | 171 | 506.00 | 5.532 | 712 | 3.848 |
| flat512 | 182 | 139 | 503.85 | 5.988 | 540 | 2.942 |
| unique512 | 235 | 164 | 506.59 | 6.000 | 695 | 3.752 |
| unique_flat512 | 182 | 139 | 503.85 | 6.000 | 540 | 2.942 |
| anchor2_flat512 | 208 | 150 | 505.35 | 5.974 | 606 | 3.287 |

control512 exactly replays prior breadth512_6 for all607inputs. flat512 removes sqrt(1+rank) only during seed selection. unique512 prefers a feasible unused entity over repeated entities; it permits repeats once no unused entity fits. unique_flat512 combines both. anchor2_flat512 keeps the original rank penalty for the first2seeds, then removes it. Protecting seeds is not a guarantee to preserve final intervals/hits under a shared token budget. Expansion retains original rank tie breaks.

| Arm versus control512 | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control512 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| flat512 | 14/69 | -15.03 [-19.61,-9.82] | 21/53 | -8.74 [-13.19,-4.49] |
| unique512 | 3/5 | -0.55 [-2.46,+1.51] | 4/11 | -1.91 [-4.37,+0.00] |
| unique_flat512 | 14/69 | -15.03 [-19.61,-9.82] | 21/53 | -8.74 [-13.19,-4.49] |
| anchor2_flat512 | 13/42 | -7.92 [-12.83,-2.92] | 14/35 | -5.74 [-9.69,-1.97] |

All intervals are exploratory4000-resample repository bootstrap (seed20261023), unadjusted across repeated adaptive research. Same cap is not identical actual usage. Mean cost/entity counts use607inputs; target coverage and density use366exactmapped tasks/77repos.370nominal exact-label tasks include4unmapped;237other label-grade inputs are not in the changed-line coverage denominator. All607inputs have been seen in development. No fresh independent admission is established.

## Post-freeze aggregate loss diagnosis

| Arm | Visible | Candidate absent | No target entity chosen | Target entity chosen, wrong region |
|---|---:|---:|---:|---:|
| control512 | 237 | 23 | 66 | 40 |
| flat512 | 182 | 23 | 137 | 24 |
| unique512 | 235 | 23 | 60 | 48 |
| unique_flat512 | 182 | 23 | 137 | 24 |
| anchor2_flat512 | 208 | 23 | 92 | 43 |

This is scorer-only analysis after every output was frozen, not label-guided PI generation. Candidate overlap can refer to an enclosing class or long function, so high candidate recall is not precise window relevance. Counts describe the failure categories, not proof of an untested causal mechanism. No per-case scores or source targets were exported or used for tuning.

## Validation and scope

Seven local and seven Linux synthetic contracts pass, including exact control, rank intervention, entity preference/fallback, full-source equality, no input mutation and cache equivalence. Actual offline Qwen607x5generation passes token caps, exact roundtrip, complete source-line equality and nonoverlapping windows. Whole source lines do not guarantee complete semantic/control-flow units. Shared per-input tokenizer caches make per-arm timings unsuitable as independent latency benchmarks.

Four source-only CPU shards each deny12label/prior-score paths using actual Landlock. All607outputs exactly replay the prior control. Generation is frozen before scoring; score and aggregate loss diagnostic exit0. Reviewed23inputSHA manifest and bash syntax pass. Windowsbackup archive/r7_before_entity_allocation precedes document edits. Windows source authority -> WSLrsync dryrun/review/sync/SHA -> bash ops/entity_allocation_r7.sh. Only these3publicreports downloaded; private inputs/IDs/labels/scores remain remote.

Frozen7/R6runtime and independent confirmation unchanged. No GPU/model/optimizer/training launched this round; no active job remains. Runtime192/128/4096 and formal start_full97.sh exit78 remain unchanged. New R7 variants are development experiments, not admitted runtime replacements or evidence of RL benefit.

AGGREGATE.json SHA 888113e3970289245208dbdb5c74a93f0929f9b4124332e86ee91b440b9c6e39
FROZEN.json SHA c31e58197857c33b5c758dafd3b4baf4b9ced27cefa6ad5632de677914ac832a
LOSS_DECOMPOSITION.json SHA a83e83463e360453cf16b97b4f5b3579272819a12565cfe9b861d7e5963c7c0b
