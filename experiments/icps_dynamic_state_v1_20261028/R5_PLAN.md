# R5 development: retain old evidence before adding executable windows

Frozen before generating R5 outputs. R4 and its failed independent confirmation remain unchanged. This round uses only the existing 607 development captures and a label-denied generator. No confirmation inputs or outputs are read. Budgets and candidate pool stay fixed; no online runtime or training changes.

R4 development loss audit: 16 old hits were lost, 14 still have a fitting target proposal but all rank below the first five; only two touch excluded declaration/docstring lines and all have executable targets. Another 57 candidate-contained tasks miss both methods, with 47 fitting proposals. These overlapping diagnostic categories suggest competition/ranking, not just token capacity. Coordinates are scorer-only and must never select runtime windows.

Compare exactly two new fixed rules with old S1 and frozen flow_expand:

1. guard_expand: preserve every current old-S1 window, encode compactly, then add ranked executable windows or adjoining source using only residual budget. If compact encoding cannot fit, return the current old-S1 representation unchanged. This is same-current-state preservation, never a stale PI fallback. All old visible lines must remain visible.
2. anchor_expand: preserve the first current old-S1 retained window; add ranked flow windows under the same 192 budget and maximum three windows, then expand locally with remaining tokens. This sacrifices the universal preservation guarantee to allow additional candidate coverage. No fitted thresholds or label-based branch selection.

Both retain exact current whole source lines, disclose partial windows, use existing issue scoring and the same candidate identities. Never exceed 192 tokens or three windows. No labels, locations, rewards, hidden tests or extra model calls. Mechanism contracts and all607 frozen-flow control equality are required before interpreting scores. The primary development gate remains +5 percentage points versus old S1 with nonregressing full targets; any selected new method needs a fresh independent cohort excluding all previous development/confirmation identities. R4 confirmation is not rerun to pick a rule.

These are W0 allocator prototypes; dynamic lifecycle, online/Harbor, causal gather, SAO parity and eight-GPU gates remain pending even if development improves.
