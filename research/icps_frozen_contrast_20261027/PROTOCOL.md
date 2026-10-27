# ICPS frozen Critic contrast

This diagnostic tests whether existing ICPS v1.1 Critics use the semantic content
of PI on fixed trajectories. It does not update either model or interrupt training.
GPU results are pending; CPU cache and layout validation are complete.

## Fixed comparison

- Checkpoints 20, 30 and 40 from the same ICPS v1.1 full97 r2 experiment.
- The same 32 trajectories from 16 repository families at every checkpoint.
- Four views: true PI; equal-length neutral tokens; equal-length PI from a different
  repository family; history alone. True, neutral and wrong-source views have
  identical Actor tokens, action mask, PI positions and value-gather indices.
  History alone necessarily changes context length and positions.
- Two forwards per view estimate numerical repeat variation. Native 8-GPU SP8
  Critic inference, native head/freeze and no loss, optimizer step or backward.
- Per-rank model fingerprints before and after must match. Load only Critic model
  shards; do not load optimizer, RNG or scheduler state. Checkpoints are read-only.

## Why these trajectories

Existing historical archives contain PI metadata, not all original PI payloads or
sampled-token tensors. Reconstructing an arbitrary evolving workspace would invent
evidence. This cohort therefore uses archived W0 snapshots and only trajectories
whose PI state is constant after the initial insertion. Reconstructed initial
state hash, window metadata and token length must exactly match the retained audit.

The population scan found 2591 attempts, 517 with available snapshots, and 139
eligible constant-state attempts. Selection uses a fixed hash order, before reading
rewards. The first CPU pass imposed an unnecessary 32768-token Actor cap and yielded
20 rows. Before any model result was inspected, the final cap was expanded to the
native Actor reserve of 73728, with response length at most 65536 and no truncation.
The final cache has 32 rows, 26 successes and 6 failures, all scored.

Actor history uses the actual proxy's canonical per-message rebuild path. It is
identical across views, but must not be described as the original sampled-token
archive. The log's deliberately forced history-rebuild messages are expected in
this CPU preparation, not evidence of a training failure.

This is an off-policy, training-task, initial-only diagnostic. It does not establish
held-out utility or cover dynamic PI updates. Neutral/wrong PI are interventions
that may be out of distribution. No oracle information, new verifier, task execution,
generation, test outcomes or future workspace state enter PI.

## Measurements and interpretation

Report task-balanced terminal-target MSE, signed calibration bias, task AUC,
early/late action-quarter MSE, paired value changes and per-view repeat variation.
Positive control-minus-true MSE favors true PI. Use repository-cluster bootstrap
intervals; these are exploratory, not multiplicity-adjusted confirmatory tests.
Recompute the actual SAO skip-observation GAE with length-adaptive lambda and the
same offline batch. This shows sensitivity of advantages, not an actual Actor
update or the original batch64 whitening behavior.

- Stable value changes and lower error with true PI support useful PI use on this
  cohort. Check whether this effect weakens from checkpoint20 to checkpoint40.
- Changes with no error benefit indicate sensitivity, not useful learning.
- Differences near repeat noise indicate little measurable semantic dependence
  in the existing Critic on this cohort; they do not prove PI contains no signal.
- To separate unused information from unusable information after a null result,
  a separate capacity-controlled, repository-held-out readout or supervised Critic
  experiment is needed. It must preserve split/targets and compare H versus H+PI
  under equal capacity. No such training experiment is launched by this queue.

## Resource isolation and execution

The queue waits for the protected current training run to exit successfully and
then requires all eight GPUs to have no compute processes and less than 1000 MiB
used, no Ray processes, and at least 200 GiB free. It repeats the idle checks after
30 seconds and before each checkpoint. A failed/stopped training run does not
release this queue to compete with a possible repair or continuation.

No stop signals, global Ray/Docker cleanup, downloads, pip installs or production
source changes occur. Each source/cache hash is checked. A frozen-forward failure
is preserved and stops the queue without automatic retry. The wait expires after
one week. A running training job is never considered hung merely to acquire GPUs.

Private caches, model outputs, trajectories, logs and detailed per-task receipts
stay on the server. Public versioning contains diagnostic code and aggregate CPU
validation only. The GPU completion artifact is FINAL_CONTRAST.json; its absence
must never be reported as a completed model test.
