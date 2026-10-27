# ICPS v1.1 — full97 source snapshot

This directory versions the actual ICPS v1.1 / 192-token source used for the independent full97 r2 experiment. It is an archive and review surface, not an instruction to launch a second job.

## Design

The host selects up to three issue-conditioned Python functions/classes from the initial buggy workspace. Before each model generation it resolves those fixed identities in the current workspace and serializes contiguous 7/5/3-line source windows (with a single-line fallback). Initial PI is capped at 192 tokens; changed states at 128; the episode PI budget is 4096. Unchanged states are deduplicated. PI is causal and Critic-only; it never includes gold patches, task verifier output acquired separately, future state, or additional task tests.

The native SAO value head, attention/visual freeze policy, losses, reward, GAE, optimizers and Actor sampling are retained. Packing follows the historical SAO phases: Actor/Critic train14336/20480 through20; 16384/45056 from21. Critic inference32768 and Actor/ref logprob14336 stay fixed. Old repair-state V2 instead used the larger training packing budgets from step1. These differences and uncontrolled rollout randomness preclude a strict single-factor causal claim.

## What is tracked

- `core/`: initial selection and read-only workspace capture.
- `src/`: window serializer, runtime integration, native packing adapter, completion/checkpoint/storage and aggregate metric helpers.
- `runtime/`: exact opt-in module overlays and their original source comparison files; `SOURCE_DIFF_RECEIPT.json` is required by the import hook.
- `tests/`: original CPU regressions and environment-dependent preflight probes.
- Site launch source, config and the Oct27 checkpoint40 resume entry.
- `results/`: aggregate training/evaluation records, not raw logs or trajectories.
- `VERSION_SOURCE_SHA256.json`: byte hashes for the archived source; `DEPLOYMENT.sha256` is the original37-file runtime manifest.

No weights, datasets, checkpoints, model caches, raw trajectories, local deployment evidence or credentials are included. Source files are byte-preserved; known serializer edge cases are documented rather than silently repaired.

## Environment boundary

A Git clone alone is not a runnable replica of the offline A800 environment. The inherited application tree is based on repair-state V2 commit45d6974. Existing private verl/Harbor checkouts, pinned shared dependencies, the original6248-task dataset/prepared-image identity manifest and site-specific preflight/namespace receipts are prerequisites. The launch scripts deliberately fail without those receipts. Do not install into shared environments or run the historical fresh launcher against an existing experiment. No deployment or training is performed by this publication.

## Validation

On 2026-10-27 the authoritative local source ran31 CPU tests with unittest discovery, all passed. This includes9 full97 contract tests requiring the existing private source/provenance fixtures. The portable serializer subset (19 window +3 budget-edge tests) can run from this snapshot:

```powershell
python -B -m unittest discover -s experiments/icps_v11_full97_sao_20261024_r2/tests -p test_windows.py -v
python -B -m unittest discover -s experiments/icps_v11_full97_sao_20261024_r2/tests -p test_budget_edges.py -v
```

The whole test_full97 suite also needs its historical trainer/native-engine and backup/provenance fixtures; those are not uploaded. No new GPU numerical validation was performed for publication. Prior byte/AST/CPU checks do not prove every future input or PI usefulness.

## Results and limitations

Raw Verified500 scores at20/30/40:273/268/280 (54.6/53.6/56.0%). SAO:262/286/291. Old repair-state V2:274/285/280. ICPS40 and SAO30/40 each have one missing original verdict.12 independent low-concurrency supplements produced11 valid verdicts,4 passes and one unresolved verifier timeout (django10097 atstep30; original reward1). No best-of or spliced formal score is reported.

As of Oct27 15:48CST, the main experiment had resumed checkpoint40 and step41 was active without a complete new step. This is a historical observation, not an evergreen status. See [results](results/RESULTS_20261027.md) and [versioning](VERSIONING.md).

Known CPU-reproduced serializer edges: an atomic status may not fit near budget exhaustion without an explicit exhaustion marker; partially missing fixed candidates may not be individually identified in visible PI. Their incidence and impact in this run have not been established. Repeat-update numerical reproducibility remains unresolved; checkpoint load success is not a bitwise guarantee.
