# R7 window selection and information-density experiment

Five new hypotheses and two controls, all with256-token initial cap and max3windows. Same607 historical development inputs;366 exact-mapped task targets in77 repositories. Target intersection is a task-level source-location proxy, not repair success. Token means below cover607; density covers the same366 tasks as coverage. Labels are scorer-only.

| Rule | Pool | Visible tasks | Full target tasks | Mean tokens | Target lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| base3 | 3 | 179/366 (48.91%) | 128 | 246.91 | 5.846 |
| base6 | 6 | 170/366 (46.45%) | 112 | 248.88 | 5.117 |
| rank6 | 6 | 188/366 (51.37%) | 137 | 248.57 | 6.134 |
| diverse6 | 6 | 197/366 (53.83%) | 130 | 249.76 | 5.867 |
| atomic3 | 3 | 166/366 (45.36%) | 125 | 242.81 | 5.583 |
| atomic_rank6 | 6 | 176/366 (48.09%) | 139 | 244.23 | 6.181 |
| compact3 | 3 | 126/366 (34.43%) | 41 | 76.42 | 5.809 |

`rank6` discounts window utility by sqrt(1+retrieval rank), preserving the ordinal retrieval preference lost by the original local-window competition. `diverse6` additionally divides utility by1+already selected windows from the same entity. `atomic3` adds up to24 complete1..8-line AST statement proposals per entity to existing context proposals. `atomic_rank6` combines statements and rank prior. `compact3` uses the atomic pool without residual contiguous expansion. All coefficients and variants were declared before generation; no per-case result tuning.

The strongest task coverage is diverse6:179->197 (+4.92pp),30 gained/12 lost; exploratory repository-cluster95% interval+1.90 to+8.64pp. Mean tokens246.91->249.76 (+1.16%). Full-target128->130 is only+2 and its interval crosses zero. Target-line density5.846->5.867 is only+0.37%; hit-task density improves8.39%. This improves breadth, not substantially more target lines per token.

The balanced comparator rank6 reaches188 visible/137 full targets with248.57 mean tokens. Target-line density improves4.93%, but visible-coverage CI[-1.12,+6.59]pp crosses zero. This is a useful development hypothesis, not established independent benefit.

Atomic proposals alone lose13 visible tasks. Atomic+rank reaches139 full targets and6.181 target lines/1000tokens but only176 visible tasks, so it does not jointly improve the objectives. Compact3 has a misleadingly high4.49 hit-tasks/1000tokens and11.75% visible target-line fraction: it reduces mean tokens to76.42 while losing53 task hits and87 full targets. Reject the strong-compression path as a joint coverage/completeness candidate. Preserve all negative results.

Retain diverse6 as the coverage candidate and rank6 as the depth/density comparator. Further work should preserve coherent target context while distributing windows across candidates, rather than simply maximizing short statements or filling more candidates. Module-level/decorator/multiple-changed-unit representation remains a separate experiment. Do not call either candidate production-ready or transfer frozen R6 confirmation/GPU evidence. A new chosen method requires its own freeze, independent confirmation and integration checks.

Validation: local15 byte-tokenizer synthetic combinations plus complete multiline-statement/docstring checks; remote actual Qwen607 inputs x7arms, source roundtrip/coordinates/non-overlap/max3/cap checks. All607 fresh base3/256 outputs exactly equal prior baseline. Four deterministic generator shards grant only individual prior files; four original label/score paths are actually inaccessible under Landlock. All generation manifests complete before separate scoring. Queue exit0. Frozen7 and runtime unchanged; no model, GPU, optimizer, formal training or private-data export.

Interpretation limits: reused development data, five-variant selection and exploratory unadjusted intervals; density is a location-evidence proxy, not semantic value or learning benefit. Control serialization is cached, so do not compare control timing to new-variant timing. W0-only; update128/episode4096 and runtime192 initial remain unchanged.
