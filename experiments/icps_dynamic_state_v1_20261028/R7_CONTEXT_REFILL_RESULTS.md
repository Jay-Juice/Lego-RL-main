# R7 fixed1024 context-refill follow-up

Neither follow-up meets the predeclared joint objective. Keep the original fast1024/8 baseline:272/366any (74.32%),238/366full-all (65.03%),935targetlines,density2.573574,mean998.57tokens. The fixed1024budget is not increased and no runtime method is replaced.

Joint+refill reaches267any/229full,931targetlines,density2.555298 (-0.71%),mean1002.02tokens and1.029s mean versus1.643s control (-37.36%). Any3gained8lost CI[-3.54,+0.27]pp;full14gained23lost CI[-5.88,+0.38]pp. It is faster but does not improve coverage or density.

Centered+joint+refill is the better depth/speed comparator:268any/237full,953targetlines,density2.625055 (+2.00%),mean997.33tokens and1.146s mean (-30.22%),median1.034vs1.695,P952.110vs2.665. Any6gained10lost (-1.09pp,repo95%CI[-2.99,+0.86]pp);full17gained18lost (-0.27pp,CI[-3.49,+3.61]pp). More aggregate target lines and density do not satisfy taskcoverage improvement; non-significant negative change is not proof of equivalence/noninferiority. Reject as replacement, retain only developmental cost/depth comparison.

Refill preserves all previously selected joint source intervals and recovers10any/34full from joint257/195, or9any/43full from centeredjoint259/194, without changing candidates/seeds. Thus some context omitted by the zero-positive-signal stopping rule carries true target evidence; low query-match score is not proof of irrelevance. Full restoration does not eliminate remaining placement differences: entitymisses45/43 unchanged and wrongregion41->31/32, compared with control26. Candidateabsence23unchanged. This is evidence about these concrete constructors, not proof that every low-score line is necessary or a universal budget lowerbound.

Across both experiments, no arm raises finaltaskcoverage+density while preservingfulltargets. Stop this bounded allocator study and retain1024/8. No independent/generalization/RL claim, no runtime promotion. Further research would need a more informative issue-to-code relevance signal calibrated separately from this reused cohort, rather than further budget increases, zero-score pruning or blanket window-count changes. No learned ranker was implemented or started this round; no extra online retrieval or neural calls.

## Coverage and density

| Arm | Any /366 | Full-all /366 | Target lines /1320 | Mean tokens /607 | Target lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| control1024_8 | 272 | 238 | 935 | 998.57 | 2.574 |
| joint_refill1024_8 | 267 | 229 | 931 | 1002.02 | 2.555 |
| joint_centered_refill1024_8 | 268 | 237 | 953 | 997.33 | 2.625 |

## Constructor timing

| Arm | Wall mean / median / P95 (s) | CPU mean (s) | Mean tokenizer misses | Median paired wall ratio |
|---|---:|---:|---:|---:|
| control1024_8 | 1.643 / 1.695 / 2.665 | 1.643 | 1443.7 | 1.000 |
| joint_refill1024_8 | 1.029 / 0.928 / 1.875 | 1.029 | 912.0 | 0.648 |
| joint_centered_refill1024_8 | 1.146 / 1.034 / 2.110 | 1.146 | 1031.5 | 0.715 |

## Paired comparisons and diagnosis

| Arm vs control | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control1024_8 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| joint_refill1024_8 | 3/8 | -1.37 [-3.54,+0.27] | 14/23 | -2.46 [-5.88,+0.38] |
| joint_centered_refill1024_8 | 6/10 | -1.09 [-2.99,+0.86] | 17/18 | -0.27 [-3.49,+3.61] |

| Arm | Visible | Candidate absent | Entity not chosen | Chosen entity, wrong region |
|---|---:|---:|---:|---:|
| control1024_8 | 272 | 23 | 45 | 26 |
| joint_refill1024_8 | 267 | 23 | 45 | 31 |
| joint_centered_refill1024_8 | 268 | 23 | 43 | 32 |

Three arms fixed1024cap/max8windows/samepassage24candidatepool. New arms freshly run unchanged joint allocation, then original linewise contiguous expansion with query-overlap priority/cost/rank tie-break. No new seed, retrieval, model or learned reranker. Every prior joint source interval must remain covered; actual607per-arm preservation checks pass. Refill can include zero-query lines bridging useful context. Exact Qwen cost admits every expansion. Whole lines/disjointsource spans/partial disclosure preserved, not semantic closure. See R7_CONTEXT_REFILL_PLAN.md.

This follow-up was declared after the first-stage aggregate outcomes. It is adaptive development on the same607seeninputs (366mapped/77repos), not independent validation; no percase label/score use for selection and no R6confirmation access. All outputs freeze before separate scoring/diagnosis. Candidate343fixed. Any-hit is at least one target changed line; full-all is every mapped target line, not semantic sufficiency. Density is targetlines/1000actualPI tokens over366tasks; mean token count over607. Bootstrap4000reporesamples, unadjusted exploratory intervals.

Fresh tokenizer cache perarm/task, rotated armorder within4CPUworkers. Timings include fresh joint+refill/source resolution/proposals and exclude initialretrieval/I/O/import/tokenizerinit/contracts/Criticcompute. Current pairedcontrol is the comparison; no cached frozen payload used to claim speed. No production latency measurement or runtime/episode integration.

4local+4Linuxcontracts passed;35inputSHAmanifest/bashsyntaxpassed;607controlpayloads exact against priorstage and607jointspan preservation checks per newarm. ActualQwen cap/roundtrip/full-source-line/nonoverlap every output.15existing label/prior-score paths denied perworker; three arms607generationoutputs froze before scoring. logs/context_refill_r7 exit0. No new failure in follow-up; first-stage nonexistent-memo-score guard exit1 remains archived. Windowsauthority/reviewedWSLpreview-sync/SHA. Only3aggregate/freeze reports downloaded; privateinputs/labels/IDs/results remainremote.

No newGPU/model/optimizer/training/runtime changes. Frozen7 and192/128/4096 runtime retained; start_full97.sh exit78. No active jobs. Results do not establish RLbenefit or independent admission.

AGGREGATE.json SHA baa6b469e9777ea548e040797f7e78e0212610e7a54f9fdcb1101155ad43cbf0
FROZEN.json SHA 37b3816412f7396a4df11006acdce5e86727e6dad184dcb289f1ffd4188f9400
LOSS_DECOMPOSITION.json SHA 4f2ec3aa52e89607f67a287ab34bd749db21916cc1f6dd3ae1eac8a9020f0d9f
