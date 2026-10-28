# Fixed-budget entity-selection experiment, declared before scores

Windows D:/ai project/RL学习/Lego-RL-main is source authority. WSL /mnt/d/ai project/RL学习/Lego-RL-main; SSH A800; remote /media/ubuntu/D1/zsj/Lego-RL-main. Independent R7 development; frozen R6/runtime unchanged.

Latest diagnosis: fixed3slot budgets leave98target-entity selection misses;6slots leave66. Candidate pool343/366 contains the target, but correct entities compete with cheap high-ranked regions. The current score divides by sqrt(1+candidate_rank), as well as novelty/cost/same-entity penalties. At rank24 the prior multiplier is1/sqrt(24), regardless of window content. This is an explicit source-level mechanism, not proof the penalty is wrong. Six slots already average5.53distinct entities, so hard diversity has limited remaining scope and may harm useful context.

Five arms, ALL512token/max6window, exact saved passage24 candidates and original source-window proposals:

1. control512: exact prior breadth512/6 (237any,171full in prior aggregate; replay every payload).
2. flat512: remove only the candidate rank penalty during seed selection.
3. unique512: retain original rank penalty, prefer a feasible previously unselected entity over every repeated entity; when none fits, allow repeats.
4. unique_flat512: combine2and3.
5. anchor2_flat512: retain original scoring for first2seed selections; remove rank penalty for later selections. This protects seeds, not final intervals/hits after shared-budget expansion.

All other score components, same-entity penalty, tie order, rendering, costs, source integrity, contiguous-line expansion and initial candidate order unchanged. Expansion still uses original rank tie breaks. No learned/semantic model or case-specific weights. The experiment is a causal ablation of existing allocation, not a semantic-reranker implementation. No additional budget or slot increase.

Use all607reused development inputs,366exactmapped targets/77repos. Source-only generation under per-file Landlock grants; deny labels and all prior-score paths. Freeze all607x5outputs before scoring. No R6confirmation/per-case tuning. Actual offline Qwen tokenizer, exact per-input caching, source equality/roundtrip/nonoverlap/cap checks. The original768/6 result251/366 remains a historical higher-cost comparator, not a same-budget control.

Report every arm: any and full-all target hits, gained/lost and exploratory repository-bootstrap intervals vs control, target-line density, actual tokens, window/entity counts. Also report post-freeze aggregate entity-selection vs wrong-region misses and selected candidate rank bands, never individual targets. Ineligible rows have no target metrics and must not be indexed as if mapped. Frozen generation source hashes must stay stable through scoring; scoring never changes output selection.

No training/GPU/model update, no runtime promotion from development alone. A negative result should reject the ablation, not trigger per-case heuristic tuning. Next independent axis would be fixed offline semantic relevance with repository-separated evaluation, which is outside this bounded experiment.
