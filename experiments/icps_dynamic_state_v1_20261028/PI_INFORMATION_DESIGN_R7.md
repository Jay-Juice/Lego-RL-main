# PI information design: next revision, R6 baseline preserved

User direction on 2026-10-28: prioritize real GPU validation or substantive PI
information design; stop expanding generic launch/dependency checks as the main
research output. Disk was subsequently cleared and the fresh resource check passed.

A direct call to the frozen R6 candidate selector on three new synthetic source
pairs reproduced these candidate-level omissions. No confirmation examples,
labels, model calls, tokenizer coverage or RL measurements were used.

| Synthetic change | Frozen R6 selection | Missing observation |
| --- | --- | --- |
| Add new.py with first(x): return x+1 and second(x): return x-1 | first plus unchanged anchor | second is never offered, despite a free third candidate slot |
| Change module LIMIT=10 to LIMIT=20 above compute(x): return min(x,LIMIT) | compute only | changed constant line lies outside every selected entity |
| Change @cached(10) to @cached(20) above compute | compute only | decorator lies before the selected def-line range |

The causes are precise: dynamic_candidates chooses one smallest entity per diff
interval, so a whole added file collapses into one entity; parse_file indexes only
function/class ranges; function ranges begin at def, excluding decorators. These
are input-representation omissions, not proven historical training bugs or measured
RL regressions. Candidate omission does not quantify final tokenizer-level coverage.

Proposed R7 experiment, kept separate from frozen R6:

1. Assign each changed source span to its smallest enclosing source unit, keeping
   all distinct sibling units before ranking. Do not select one entity for an entire
   multi-entity diff interval. Keep the existing maximum three emitted windows.
2. Extend source units to decorator spans and module-level executable statements
   (assignments/imports). Their exact current-source coordinates and kind must be
   explicit; do not invent a function identity for them or add semantic fix claims.
3. Under the same 128-token update cap, prioritize distinct changed units and their
   minimum coherent context before adding unchanged issue anchors or expanding a
   selected window. Initial 192 and episode 4096 caps remain fixed. Preserve retry,
   causal timing, rollback, unknown/limited and whole-window omission semantics.
4. Measure changed-unit availability, emitted changed lines, per-unit context,
   metadata/token share and useful changes retained before budget exhaustion. Do not
   optimize for emitting more lines indiscriminately. Compare real Qwen-tokenized
   outputs to R6 on synthetic cases and the existing development cohort only.

Run the multi-entity correction separately from module/decorator units so their
benefits and losses can be attributed. Initial candidate recall and caller/callee
context are later hypotheses; do not add them simultaneously without evidence.
Any method change requires its own freeze and genuinely independent confirmation;
the R6 confirmation cohort must not be reused to select or tune R7. R6 stays the
GPU probe baseline. Native training recipe/head/freeze/reward/filter are unchanged.

No R7 runtime implementation, deployment, new coverage claim or model update has
been made. Resource readiness now permits completing the existing disposable GPU
probe path; its remaining launch implementation must be finished without treating
this design note or a resource snapshot as launch approval.

## Development budget/pool evidence after human budget authorization

The six-arm W0 factorial is implemented separately and complete; see R7_BUDGET_RESULTS.md. It is not a deployment of the changed-unit design above. Pool3/256 improves visible171->179 and full105->128 on366 development targets. Pool6 improves candidate242->282 but reduces visible hits at every matched cap. Prioritize candidate-to-window ranking (retrieval prior vs local window utility) rather than simply doubling candidates or budget. Keep module/decorator and multi-unit dynamic corrections separate. No R6 confirmation reuse, no runtime budget change, no transferred GPU/independent-admission claim.

## Window research outcome

Predeclared seven-arm development run is complete (R7_WINDOW_RESEARCH_RESULTS.md). At the same256 cap, ordinal retrieval prior and a same-entity window-repeat penalty improve task coverage179->197 with essentially unchanged mean tokens. The improvement is breadth: full-target only128->130 and target-line density only+0.37%. Rank-prior-only188/full137 gives a more balanced point estimate and+4.93% target-line density, but its coverage CI crosses zero. Whole short-statement proposals and no-expansion compression do not jointly improve objectives. Keep diverse6/rank6 as development comparators; next focus is coherent context retention under cross-candidate diversity. No runtime integration or independent confirmation; module/decorator/dynamic-unit proposal remains separate and unimplemented.
