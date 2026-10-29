# R7 real historical trajectory replay

The cached1024_8 W0 PI passes transport through the actual Critic builder on all
607 archived real Actor trajectories, from 30 original training batches. R2
verifies each batch SHA against the fixed manifest, its task/row identity, and
each frozen PI artifact SHA against the entity-evidence generation receipt.
No new selection or label scoring occurs in this test. Historical containers
include rewards, but only the explicit Actor tensor allowlist and call spans
enter the replay. Old PI, rewards, returns and advantages are not injected.

Both attempts exited 0. The initial attempt is preserved; R2 adds batch SHA,
task-row identity, independent Actor tensor copies, and loss-mask equality.
Current source manifest refers to R2. Initial source is retained under
archive/r7_trajectory_replay_initial, not to be rerun with current bytes.

## Result

- 607/607 pass; 27,660 historical call boundaries checked.
- All 606,133 frozen W0 PI tokens survive unchanged in the actual Critic view.
- Removing PI recovers the exact Actor token stream. Actor tensors, response
  mask, loss mask and stored log-probabilities remain unchanged.
- Native packed value gather agrees with every response pre-token position.
  A positional tensor backward pass gives exactly the expected gather gradient.
  This is not a neural-network value, loss or parameter-gradient test.
- Empty PI restores Actor sequence/mapping exactly; later-call extension leaves
  earlier input prefixes unchanged.
- Maximum Actor length 73,106; maximum Critic length 74,121. No PI-budget omission.
- R2 elapsed 104.496 seconds; mean measured view work 0.097661 seconds per task.
  This includes direct interleave, actual builder, gather/backward and comparisons;
  excludes PI construction/retrieval and is not training throughput.

The complete payload preservation means the previous W0 annotation scores
(272/366 any, 238/366 full-all) are not reduced by this replay's packing. Those
scores were NOT newly measured on online states, nor are they independent
validation results. All 607 research samples occur in the current 6,248-row
training parquet. Historical 516/36/55 labels describe internal research splits;
repeated method development has consumed the whole cohort as development data.

## Limits and training decision

This uses actual historical Actor tensors, not a newly generated model rollout.
Only the first call gets W0 PI; later calls intentionally receive empty PI because
the archive does not contain complete per-step workspace snapshots. The frozen
W0 capture has HEAD=null for all607, not a conflicting recorded commit. Its
declared base image matches the historical manifest in607/607, but that alone
does not prove complete prepared-workspace identity. No source-identity gate is
marked passed from this comparison.

No GPU/model/optimizer was launched. Frozen R6/runtime is unchanged. This result
establishes real-trajectory transport/Actor isolation for cached1024_8; it does
not establish dynamic coverage or the new method's neural numerical behavior.
Formal training remains disabled. Next required acceptance is a fresh online
R7 workspace/Actor trace plus the current method's native numerical short test;
the earlier successful R6 eight-GPU probe does not automatically cover R7.
