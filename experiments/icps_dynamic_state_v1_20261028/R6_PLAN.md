# R6: marginal issue information under the fixed token budget

Predeclared before new outputs. Only original607 development data; no confirmation examples. Frozen R4 and all R5 sources remain unchanged. No online or training code changes.

Signal audit: 12/16 R4 regressions contain a pair of selected windows with query-set Jaccard >=0.5. A target proposal includes a still-unseen issue term in 9/16 regressions and 34/57 candidate-contained cases missed by both methods. These are overlapping scorer-side descriptions, not proof of causal utility. Labels/target coordinates never enter generation.

Reuse exactly the R4 flow proposal pool, candidate identities, render and local residual expansion. At each greedy choice compute repeated_fraction = |window_query_terms intersect selected_query_terms| / max(1, |window_query_terms|). Two fixed variants:

- novelty_expand: utility = existing R4 score / (1 + repeated_fraction). No change to the first-window score, no mandatory equal allocation to candidates, no hard rejection of repeated but relevant evidence.
- novelty_cost_expand: the same utility divided by sqrt(max(1, actual marginal token cost)). This additionally tests token efficiency; it can change the first window as well.

All ties follow the frozen proposal order. Select at most three disjoint exact windows within 192 actual tokenizer tokens; fill residual space using the unchanged local expansion rule. If no proposal fits, use the existing current-source R4 explicit/minimal fallback. No stale states, synthetic bug location, extra model or oracle. W0 prototypes only; 128/4096 and dynamic lifecycle remain inherited and not admitted for these variants.

Run mechanism contracts and the same607 label-denied paired generation with exact frozen-flow control. Primary development criterion stays +5pp and nonregressing full target versus old S1. Retain all results, including negative ones. Do not probe the old220 confirmation to choose a variant. Any future promoted method must use a fresh independent cohort and all remaining runtime/Harbor/causality/8GPU/SAO/resource gates.
