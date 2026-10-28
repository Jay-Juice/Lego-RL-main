# R7 candidate recall experiment results

Same607 development inputs,366 mapped exact-target tasks in77 previously seen repositories. Fixed diverse6 window allocator, cap256, max3windows; frozen R6/runtime unchanged. Mean tokens cover607; density and coverage cover the same366.

| Candidate rule | Candidate hits | Visible hits | Full target hits | Mean tokens | Target lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| base6 | 282/366 (77.05%) | 197/366 (53.83%) | 130 | 249.76 | 5.867 |
| pool12 | 308/366 (84.15%) | 195/366 (53.28%) | 129 | 250.48 | 5.844 |
| files12 | 283/366 (77.32%) | 186/366 (50.82%) | 123 | 250.82 | 5.618 |
| symbols12 | 306/366 (83.61%) | 200/366 (54.64%) | 128 | 249.73 | 5.954 |
| links12 | 301/366 (82.24%) | 194/366 (53.01%) | 126 | 250.53 | 5.840 |

base6 is the prior diverse6 experiment, exactly replayed on all607 inputs. pool12 doubles the original lexical pool. files12 retains top3 anchors and penalizes repeated files. symbols12 retains top3 anchors then fuses original body-based lexical ranks with a separate file/symbol/signature BM25 channel. links12 retains top6 plus one-hop import/same-module/member-call neighbors, filling remaining slots lexically. All rules were frozen before scores.

The candidate-recall gain is real on this development set: pure top12 reaches308 vs282 (+26, +7.10pp). It converts into only3 gained visible tasks and5 lost (net-2). Candidate-to-visible conversion falls197/282=69.86% to195/308=63.31%. Candidate pool coverage is not final useful coverage.

Symbol fusion reaches200 visible hits (+3,+0.82pp),14gained/11lost; exploratory repo-cluster95% CI[-1.92,+4.43]pp crosses zero. Full targets drop130->128. Target-line density5.867->5.954 is+1.48%; mean tokens249.76->249.73. Retain as a development comparator, not a robust improvement or deployed choice. Compared with pure pool12, symbol fusion retrieves2 fewer target cases but displays5 more, illustrating ranking/selection alignment matters.

File spreading gives283 candidates but only186 visible/123 full; reject this strong file-diversity rule. Static neighbors give301 candidates but194 visible/126 full; these syntactic connections are too weak under the current allocation to outperform the baseline. No parameter/per-case retuning follows this run.

The next substantive direction is candidate-to-window alignment: evaluate candidates using actual coherent window evidence and token cost, preserving high-confidence anchors rather than feeding larger pools unchanged into the same greedy allocator. Additional capture/representation ceilings are measured separately in SCOPE_DIAGNOSTIC.json. Module/decorator and dynamic changed-unit prototypes remain separate work.

Validation:7 synthetic tests local and7 on Linux; actual Qwen607 x5 arms, exact original top6 and previous diverse6 payload dictionaries, source coordinates/token roundtrip/nonoverlap/max3/cap. Four disjoint shards with individual baseline-file grants and five actual label/score denials each. All generated outputs hash/freeze before separate scoring; main queue exit0. Private cases stayremote. No model/GPU/optimizer/training or frozen/runtime changes.

Limitations: reused development and four new hypotheses, exploratory unadjusted intervals; no independent confirmation. Static graph is source syntax, not proven runtime binding; alias reassignment and dynamic dispatch are not fully modeled. Location evidence does not establish semantic information or learning benefit. Base6 arm timing is cache access, so do not compare it with new serialization timings.

Scorer-only availability diagnostic (exit0): all1320 target lines in these366 exact-mapped tasks are captured; current unambiguous function/class/parse-fallback union represents1314lines and363/366tasks (99.18% any,362 full-any). Three tasks lack any represented target; four have at least one target line outside the entity union.35captures are flagged limited but still contain these mapped targets. This is a label-informed union-of-all-source ceiling, not a deployable selector or proof that all lines fit/propose within256tokens. The mapped-task denominator conditions this result; do not generalize100% capture availability to607/all tasks. Within this subset, ordering and window allocation dominate the losses; module/decorator additions alone cannot explain the large gap.
