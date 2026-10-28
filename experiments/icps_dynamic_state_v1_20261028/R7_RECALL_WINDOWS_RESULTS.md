# R7 recall-to-window experiment: candidate recall93.72%, final coverage56.01%

## Outcome

The new full-body passage retrieval plus rank fusion recovers37previously missed candidate-hit tasks, with no baseline task-hit losses:306/366(83.61%)→343/366(93.72%). Final PI improves only200→205visible and128→134full-target hits at the same256-token cap. Mean token cost249.73→250.01 and target-line density5.954→6.031(+1.30%). Final visible gain+1.37pp has exploratory repo95%CI[-0.23,+2.89]pp, so robust final coverage improvement is not yet established. Candidate recall CI[+6.98,+13.29]pp is positive but remains reused-development evidence. Keep passage24 as a next-stage development comparator; no runtime promotion or100%claim.

## Why the original12candidate pool missed60tasks

On366exactmapped tasks in77repositories,57of60misses already have a target in parsed source entities. With the saved12candidate prefix fixed and the remainder deterministically ranked,21have their first matching entity at ranks13–24,16at25–48,9at49–96,and11at97or later. Three lack any target in the existing parsed-entity representation. No other miss lacks a lexical/header rank in this diagnostic. These are source-coordinate/ranking observations, not proof of semantic irrelevance or a unique cause per task.

Of those60misses,41already have the target file among the baseline candidate files;19do not. Thus the dominant problem is selecting the correct entity within available source, not simply failing to scan the repository. The original body ranking uses source[:8192]characters; the new full-body passage channel removes that prefix limit. A synthetic tail-only query verifies that mechanism, but the development result also changes rank fusion, so37rescues must not all be attributed to prefix truncation.

## Six predeclared arms

All use unchanged original diverse6 actual-code window allocation, maximum3contiguous/nonoverlapping windows and actualQwen tokenization. Symbols24 preserves every saved symbols12candidate in its original order and only appends candidates. Passage24 adds max-BM25 full-body128word passages/stride64 to original lexical and header channels, with reciprocal-rank fusion and original top3anchors retained. Free24 removes the forced-anchor prefix; explicit names/paths still contribute through the original ranking channel. No label-derived queries, target source import/execution, verifier or reward access during generation.

| Arm | Cap | Candidate hit | Final visible | Full target | Mean tokens | Target lines/1000PI tokens |
|---|---:|---:|---:|---:|---:|---:|
| base12_256 | 256 | 306 | 200 | 128 | 249.73 | 5.954 |
| base12_384 | 384 | 306 | 208 | 170 | 365.63 | 5.089 |
| symbols24_256 | 256 | 327 | 202 | 129 | 249.70 | 5.989 |
| passage24_256 | 256 | 343 | 205 | 134 | 250.01 | 6.031 |
| free24_256 | 256 | 343 | 186 | 123 | 248.84 | 6.040 |
| free24_384 | 384 | 343 | 198 | 162 | 360.48 | 5.282 |

Simple expansion12→24 recovers21candidates but only2net final visible hits. Passage fusion recovers37candidates but only5net final hits. Removing forced anchors is worse for visible/full coverage despite identical task-level candidate-hit counts343; candidate identities and their order can both differ, so this is not a pure ordering ablation. Reject free24 as a coverage/completeness improvement. Raising its budget to384does not catch the matching old384control208visible/170full.

The candidate-to-final conversion for passage24 is205/343=59.77%, versus200/306=65.36%forbaseline. The expanded pool is more complete, but final selection leaves138candidate-containing tasks uncovered. Do not mistake higher upstream recall for equivalent final utility.

## Where final PI loses the recovered information

The predeclared scorer-only fixed-proposal diagnostic exits0. All buckets reproduce366tasks and exact observed hits:

| Arm | Already visible | Candidate absent | Candidate present, no hitting seed | Fitting hitting seed not selected | All hitting seeds too large alone |
|---|---:|---:|---:|---:|---:|
| base12_256 | 200 | 60 | 6 | 100 | 0 |
| base12_384 | 208 | 60 | 6 | 92 | 0 |
| symbols24_256 | 202 | 39 | 7 | 118 | 0 |
| passage24_256 | 205 | 23 | 9 | 129 | 0 |
| free24_256 | 186 | 23 | 10 | 147 | 0 |
| free24_384 | 198 | 23 | 9 | 136 | 0 |

For passage24/256,129misses already have an original contiguous seed proposal that intersects a target and fits the actual rendered token budget when used alone. Nine need a different proposal/anchor;23still need retrieval/representation improvement. No missed case with a hitting seed is blocked by the standalone256token cost in this diagnostic. This does NOT mean256is sufficient for all target lines, dependencies or semantic completeness: one3/5/7-line hit is a much weaker requirement.

Actual final windows plus these single-window witnesses cover334/366=91.26%tasks under the cap/max3/nonoverlap constraints. This uses target labels after freezing to prove existence of a feasible hit, not to construct a deployable selector. Fixed seeds omit other expansion/window alternatives, so334is not a universal upper bound. It must not be reported as achieved PI coverage or transferred to new tasks.

Next focused experiment: keep passage24 retrieval, improve issue-to-window relevance while protecting the original high-confidence anchors and complete surrounding statements. Evaluate candidate-to-final conversion, full-target coverage and density jointly. If fitting a reranker, use repository-separated development folds with held-out scoring; these reused tasks still cannot be called fresh independent confirmation. Do not tune on R6confirmation. Separately add source-derived proposals for candidate-present/no-seed cases and address the23retrieval misses. No new reranker or runtime change is implemented in this report.

## Scope, isolation and failure history

Same607previously seen development inputs;366exactmapped targets supply coverage/full/density denominators. No independent split, no R6confirmation tuning. Full means exact target-coordinate completeness, not semantic or control-flow sufficiency. Density is visible target source lines per1000PI tokens, not mutual information or Critic/RL benefit. Candidate any-hit may include a large enclosing class. Source availability363/366is only a prior label-informed entity-union witness, not an attainable token-limited coverage guarantee.

R1 exited1before scoring when exact candidate replay caught a near-tie order mismatch. A label-free field-only diagnostic showed new and fresh old constructors identical, while fresh old differed from saved baseline at positions9/10. Header BM25's unordered query set permits floating-sum order changes. R2 retains the saved baseline/prefix exactly, validates its identities/hashes/coordinates against current parsing, and sorts new header query terms; process hash seed0. Original R1source/queue retained; R2uses separate filenames/queues and never overwrites running sources. No target scores were inspected to choose this repair. Prior frozen outputs remain valid.

R2local7andLinux7synthetic tests pass, including cross-process hash seeds1/17/103. Four generators actually deny8label/previous-score paths; every arm passes actualtoken roundtrip/source/nonoverlap/max3/cap checks;607baseline256payloads reproduce exactly. Main queue logs/recall_windows_r7_r2 exits0 after all607x6payloads freeze and separate scoring. Scorer-only miss classification is aggregate; private case IDs, source, outputs and scores remain remote. Frozen7/runtime unchanged. No GPU/model/optimizer updates or training this round.

Windows source authority; reviewed WSLrsync dryrun/sync/SHA then bash ops/recall_windows_r7_r2.sh. Reports/receipts carry hashes. This result does not enable formal start_full97.sh, which remains disabled.
