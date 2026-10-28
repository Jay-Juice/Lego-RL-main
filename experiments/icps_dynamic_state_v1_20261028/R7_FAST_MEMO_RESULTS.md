# R7 local memoization: exact output replay

This follow-up was declared and implemented while the seven-arm quality experiment was still generating. It caches file-line splitting and token-independent term extraction only within a single invocation, and hoists unchanged selected-payload costs during expansion. There is no new scoring, retrieval, budget, global module patch, or cross-task cache.

Both predeclared configurations (fast768_8 and fast1024_12) replay the entire frozen output dictionaries exactly for all607inputs each, including PI text/IDs, windows, source maps and metadata. No labels or scorer are imported;14label/prior-score paths are denied per Landlock worker. Quality is inherited from the exact reference output, not new independent evidence. This preserves full source bytes and eliminates stale cross-snapshot cache risk by construction; synthetic edited-source and module-global tests also pass.

## Fixed64-input paired benchmark

| Arm | Original mean / median / P95 (s) | Memo mean / median / P95 (s) | Median paired ratio |
|---|---:|---:|---:|
| fast768_8 | 1.062 / 1.047 / 1.714 | 0.944 / 0.937 / 1.454 | 0.885 |
| fast1024_12 | 2.065 / 2.052 / 3.682 | 1.831 / 1.830 / 3.249 | 0.892 |

Both implementations are rerun on the same first64metadata-sorted inputs, selected without labels before scoring. Order alternates per input; tokenizer caches are fresh per implementation. P95 is nearest-rank on64samples. Four concurrent workers, warm compiled functions, no initial retrieval/I/O/import/tokenizer initialization or Critic forward pass in measured time. Do not compare these64subset medians directly to the main study607medians as if paired. This is not production training latency.

The main quality recommendation1024/8 was not a predeclared memo replay arm. Its reported1.645s mean remains the measured original fast implementation on607inputs; do not silently substitute memoized timings from1024/12 or768/8. Applying this optimization to1024/8 requires its own exact replay/performance evidence. The12-slot variant remains inferior on completeness/density despite possible acceleration, and is not promoted from faster execution alone.

Four local and four Linux synthetic contracts pass;607x2actual Qwen source-only replays pass; queue exit0.28inputSHAmanifest and shell syntax pass. Frozen7/runtime unchanged. Only this aggregate downloaded; private benchmark rows/IDs remain remote. No GPU/model/optimizer/training, no active job. Windows source authority -> reviewed WSLrsync preview/sync/SHA -> bash ops/fast_memo_r7.sh. No old experiment or shared package edits.

AGGREGATE SHA 5eba17b8a9a459504551601144741e7ef997dd4e89bbb6ebeb37f632a58175ae
