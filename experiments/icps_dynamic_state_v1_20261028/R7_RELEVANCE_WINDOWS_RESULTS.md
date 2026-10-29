# R7 fixed-pool final-window relevance experiment

Outcome: both new lexical relevance fusion variants lose visible coverage, complete-target coverage and target-line density against the same-pool/same-budget original allocator. Reject all four new arms for runtime promotion. The original allocator at384 increases completeness but costs46.70% more mean tokens and loses15.34% density; keep it only as a development depth comparator. No near100% result.

| Arm | Candidate hits | Any target hit /366 | All target lines /366 | Mean tokens /607 | Target lines /1000PI tokens |
|---|---:|---:|---:|---:|---:|
| base256 | 343 | 205 | 134 | 250.01 | 6.031 |
| base384 | 343 | 213 | 174 | 366.77 | 5.106 |
| fused256 | 343 | 190 | 127 | 250.35 | 5.833 |
| fused384 | 343 | 196 | 163 | 365.92 | 4.945 |
| anchored256 | 343 | 196 | 132 | 250.26 | 5.951 |
| anchored384 | 343 | 202 | 170 | 365.75 | 5.101 |

## What was changed

Exact saved passage24 candidate pool, original seed windows, actualQwen tokenizer, max3 nonoverlap contiguous full-line windows and original context expansion. New pooled-window BM25 and original utility ranks are fused at fixed2:1 native/relevance weight, rank constant20. Anchored arms keep the original first selected seed before fusing subsequent slots. This is a lexical heuristic, not a semantic reranker; first-seed protection does not guarantee identical final expanded coordinates. No frozenR6/runtime edits.

## Coverage and completeness

Original256 gives205/366=56.01% any-target coverage and134/366=36.61% all-target-line completeness. Original384 gives213/366=58.20% and174/366=47.54%. Eight new any-hit tasks, zero lost; exploratory repo95%CI of any-hit delta[+0.78,+3.79]pp. Complete-target gain40tasks, zero lost, full-any CI[+7.85,+14.51]pp. Full-any and full-all happen to have equal counts in every arm here; they are distinct metric definitions. Full-any requires all changed lines of at least one hunk; full-all requires all changed lines of every hunk. Neither establishes semantic/control-flow sufficiency.

Fused256 gains10/loss25, net-15, repoCI[-7.45,-0.52]pp. Fused384 gains9/loss26, net-17, CI[-7.37,-1.41]pp. Anchored256 gains10/loss19, net-9, CI[-5.57,+0.82]pp; anchored384 gains9/loss20, net-11, CI[-5.59,0.00]pp. Anchor protection reduces observed damage but does not turn this fusion into a win. Do not attribute a causal failure to an individual BM25/RRF component without a separate ablation.

## Interpretation and next boundary

The pool still recalls343/366tasks; increasing a lexical score or compressing its rank does not ensure that the right code enters finalPI. Prior oracle single-seed witness334/366=91.26% only establishes that some fitting hitting seed exists; it is not achieved selection accuracy. This experiment gives no evidence that more variants of lexical fusion will approach100%. Next research should change the relevance signal: issue constraints matched to code behavior, source-derived data/control dependencies, or an offline semantic reranker, with a predeclared repository-separated development design. Any supervised fitting must segregate training repositories and evaluation outputs; R6confirmation remains excluded. No semantic reranker, learned weights or new validation split was implemented here.

100% any-hit and100% all-target-line completeness are different goals. Remaining candidate gaps, seed gaps, selection errors and finite context each remain. The measured384 budget tradeoff improves depth but is not a joint density/coverage solution. Keep256 as density comparator and384 as depth comparator; do not silently raise frozen192/128/4096 runtime budgets.

## Execution and isolation

Five local synthetic contracts and five Linux contracts pass. Four actual Landlock generators deny8label/prior-score paths; all607x6 outputs freeze before separate scoring.607original passage24_256 payloads replay exactly. Every arm passes actualQwen roundtrip/cap/source/max3/nonoverlap checks. Fixed seed0 preserves original floating-score behavior. Main queue logs/relevance_windows_r7 exits0/state complete_development_only. No healthy job remains. No new GPU/model/optimizer/training run. No private captures/case IDs/scores downloaded; only aggregate/frozen public reports. Frozen7 SHA exact.

Windows edits -> reviewed WSLrsync preview/sync ->19input SHA checks -> bash ops/relevance_windows_r7.sh. Source, manifest and outputs retained; no rerun of completed independent confirmation/Harbor/GPU stages. All607tasks previously seen,366exactmapped targets in77repos;370nominal exact-label tasks includes4unmapped.237other tasks are not exact-target scoring examples. Do not present conditional366rates as coverage over all607 or as new-repository generalization. Intervals are unadjusted exploratory reused-development evidence.

AGGREGATE SHA: ad286593f0752faeab8c0cd2fa33d7101b4348fa25f43502a017c5999ccf2eb6
FROZEN SHA: b6919b18a4584a343162b68b33ae7e5b41339848eeab7ebcde0a7145a784302f
