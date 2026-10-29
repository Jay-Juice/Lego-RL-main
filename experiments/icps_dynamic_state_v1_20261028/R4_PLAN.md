# R4 executable source anchors — frozen before new outputs

All 607 cases remain development. R3 expand (143/366 target, 88 complete)
is retained as the exact control. This round tests two fixed mechanisms, not
an unrestricted parameter search. No holdout labels or outputs are opened.

1. body_expand: rank executable source lines instead of declarations,
   docstrings and comments. Lexical evidence in code remains issue-only.
   Keep current 3/5/7-line context and residual adjacent-line expansion.
2. flow_expand: same executable anchors plus a conservative, one-hop name
   relation to the strongest three executable issue anchors within each
   candidate. Include earlier stores and return/raise consumers sharing a
   name. This is a syntactic heuristic, not proven dataflow or an oracle.
   Bonus is fixed at 1, capped per line; no transitive traversal.

Candidate pool, 192/128/4096 budgets and at most three windows are unchanged.
Actual changes retain R3 priority. Comment/docstring text is not rewritten:
it may still appear as exact adjacent context. No synthesized source enters PI.

Generation denies label access with Landlock. Freeze all source hashes before
generating all 607 outputs, then score once. Report every variant, both gains
and losses, target/full-hunk coverage, actual token cost and source density.
Development admission remains >=5 percentage points over old 129/366 with
full-hunk nonregression; a pass is not independent validation or training
permission by itself. Online/Harbor/GPU admission remains outstanding.

Validate docstring exclusion, nonlocal name relation, exact source and budget,
absence of input mutation, and changed-window priority. R3 archives and all
failed results remain preserved. No training or old source modification.
