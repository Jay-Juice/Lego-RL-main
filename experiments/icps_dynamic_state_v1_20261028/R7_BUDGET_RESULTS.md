# R7 candidate-pool and W0 budget ablation

Same607 historical development inputs,366 exact mapped targets (370 nominal,4 unmapped),77 repositories. All results below are development estimates; the R6 independent confirmation remains untouched. Coverage means task-level visible intersection with a verified changed-source target, not repair success or source-line percentage. Token averages cover all607 inputs.

| Candidate pool | Initial cap | Candidate hit | Visible hit | Full target | Mean tokens |
|---|---:|---:|---:|---:|---:|
| 3 | 192 | 242/366 (66.12%) | 171/366 (46.72%) | 105/366 (28.69%) | 187.57 |
| 3 | 256 | 242/366 (66.12%) | 179/366 (48.91%) | 128/366 (34.97%) | 246.91 |
| 3 | 384 | 242/366 (66.12%) | 189/366 (51.64%) | 159/366 (43.44%) | 359.36 |
| 6 | 192 | 282/366 (77.05%) | 166/366 (45.36%) | 92/366 (25.14%) | 188.29 |
| 6 | 256 | 282/366 (77.05%) | 170/366 (46.45%) | 112/366 (30.60%) | 248.88 |
| 6 | 384 | 282/366 (77.05%) | 183/366 (50.00%) | 152/366 (41.53%) | 363.01 |

At pool3,192->256 adds8 net visible hits (+2.19pp;9 gained/1 lost; exploratory repository-cluster95% CI+0.69 to+3.59pp). Full-target hits increase105->128 (+6.28pp). Average actual tokens rise187.57->246.91 (+31.64%). At384, visible hits189 (+4.92pp) and full159 (+14.75pp), with359.36 average tokens (+91.59%). More budget helps completeness but does not yield a large visible-recall jump.

Pool6 raises candidate recall66.12%->77.05%, yet loses visible coverage at every budget under the unchanged max3-window allocator. At192 it gains20 and loses25 tasks; at256, relative to3/192 it gains24 and loses25. These are exploratory point estimates; the paired CIs cross zero. This does not establish that larger pools are always bad. It does show the unchanged allocator fails to convert additional retrieved candidates reliably. The code ranks windows by query novelty and token cost, without directly retaining the entity retrieval score/tier in marginal utility; a retrieval-prior-aware allocator is a specific next hypothesis, not a proven improvement.

Keep3/256 as the next development comparator. Do not deploy6 candidates unchanged or promote384 merely for the highest point estimate. Improve candidate-to-window selection separately from changed-unit module/decorator representation. Preserve max-window/budget attribution. Any chosen method needs a new freeze and fresh independent confirmation; this reused development cohort is not that evidence.

R2 completes with exit0: four disjoint deterministic CPU shards, actual Qwen tokenizer, all607 baseline outputs exact, all607 pool6 prefixes exact, source coordinates/roundtrips/caps/max3 windows checked. Three known label/score paths are actually denied per shard by Landlock; scoring begins after every output is frozen. Original run used an overly broad baseline directory grant that also permitted old scored rows. Inspected code did not read that file, but original isolation is not accepted. Its source/queue/output are retained; R2 narrows permissions to specific baseline files without changing the six methods or cohort. No private inputs, per-case identities or scores are exported.

R6 frozen sources, runtime,192/128/4096 budgets and completed GPU baseline remain unchanged. Only experimental W0 caps vary here; no dynamic-update or episode exhaustion benefit is measured. No GPU, model update, new rollout or formal training in this experiment. A larger W0 payload would consume more of the same4096 episode allowance.
