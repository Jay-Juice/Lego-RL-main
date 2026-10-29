# R7 initial PI and dynamic-update compatibility

Decision: do not launch full training. The probe-only composition of current
cached1024_8 W0 and the existing128-token dynamic update has observable omissions.
Frozen R6 method/runtime remain unchanged; no runtime promotion or model run.

## Construction

The R7 W0 uses passage24: original issue/source ranking, entity-header ranking and
max BM25 over128-word source passages with64-word stride, fused by reciprocal
rank while retaining three original anchors. At most24 source entities enter
window construction. The cached1024_8 allocator uses exact source windows,
relevance/rank/cost/repetition scoring, at most8 nonoverlapping windows, followed
by context expansion. Full-payload Qwen tokenization is authoritative at each
accepted addition and at final output. AST/line/term caching and batched encoding
change construction cost, not the frozen baseline output. No labels or verifier
results enter this construction.

The new probe changes only the initial candidate builder, initial serializer and
initial cap in a process-local clone of the R6 session capture. Update budget128,
episode4096, and the existing update selector/serializer/retry/semantic dedup are
retained. This is an unpromoted compatibility experiment, not a new online release.

## Observed dynamic visibility

Actual Qwen tokenizer, synthetic source snapshots, no model/GPU/optimizer:

| Event | Required changed units | Visible | Update tokens |
|---|---:|---:|---:|
| Function body edit |1|1|26|
| New file with two functions |2|1|42|
| Module-level constant edit |1|0|0|
| Decorator edit before function definition |1|0|0|

Source slices in emitted windows are exact and same-call retries are exact in
all four cases. Ordinary rollback emits26tokens. Removing the newly added file
emits31tokens with unknown status. Constant/decorator rollback also emits nothing.
These four constructed cases are mechanism tests, not a representative dynamic
coverage rate or a fresh real Actor rollout. They do not invalidate the measured
W0 annotation scores, but refute assuming those scores cover subsequent changes.

## Cause and next change

`dense_state.dynamic_candidates` chooses one smallest entity per changed interval.
A newly added file has one interval spanning the entire file, so multiple new
functions can collapse to one candidate even when slots and tokens remain.
Module statements and decorator lines fall outside current function/class
intervals. The selected visible windows remain unchanged; semantic dedup then
suppresses the update. Increasing the128 cap alone does not create missing
candidates. The42-token new-file update specifically shows unused capacity.

The required targeted repair is to enumerate distinct owning units intersecting
changed spans, represent module executable statements and decorators explicitly,
then prioritize changed units before unchanged anchors. Preserve exact source
mapping, bounded work, retries, omission reporting and episode limits. This repair
has not been implemented or accepted by this experiment. No independent R6
confirmation data was read or used, and no model reward claim is made.

## Execution and provenance

First attempt failed during import because validation/budget_ablation_r7.py
shadowed src/budget_ablation_r7.py. Its queue and source backup are retained in
logs/dynamic_quality_r7 and archive/r7_dynamic_import_failure. The corrected
attempt logs/dynamic_quality_r7_r2 exited0 and produced status
`dynamic_visibility_gap`, which is a failed quality decision, not training
admission. Seven-file SHA manifest is validation/DYNAMIC_QUALITY_R7.sha256.
Report: reports/DYNAMIC_QUALITY_R7.json.
