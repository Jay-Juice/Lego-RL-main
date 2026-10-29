# Fixed-pool final-window relevance experiment

Predeclared before new generation/scoring. Development only, all607 previously
seen tasks; mapped366 denominator retained. Windows source authority; A800 SSH
deployment at /media/ubuntu/D1/zsj/Lego-RL-main, via reviewed WSL rsync.

Input: exact frozen passage24 from recall R2, receipt
c6c2227d8549fa391b9b454e534545b7722123b3296083f82e33c20dccaec366.
No retrieval changes. Frozen R6 and runtime untouched.

Six arms: original diverse6 baseline, window-relevance fusion, and fusion after
preserving the original first selected seed; each at256/384 actual Qwen tokens.
Fusion uses fixed2:1 native/source-window BM25 reciprocal ranks with constant20.
Native rank = original line score / sqrt(1+candidate rank); BM25 uses pooled seed
documents, k1=1.2,b=.75 and weak.25 identity-term overlap. No target labels or
trained ranking parameters. Overlapping documents can bias IDF; explicit limit.
Final exact marginal cost, repetition/diversity discounts, contiguous full-line
source, max3 nonoverlap windows and original one-line context expansion retained.
The first seed protection does not guarantee the same expanded first window.

Generate all607*6 outputs under Landlock with labels and prior scores denied;
assert607 old passage24_256 output replay exact; freeze source/output hashes,
then separately score. Compare within same pool and budget. Report candidate,
any-target, complete-target, token and target-location density, repo bootstrap.
No conditional early stop or per-case score inspection/tuning. No CI claim after
multiple adaptive development rounds; no independent confirmation transfer.

Motivation: prior scorer-only witness found129 missed tasks with a fitting seed;
that label-assisted91.26% witness is not achieved coverage or semantic utility.
100% remains an aspiration, never a fabricated denominator or tuning label.
