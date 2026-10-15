# PI-only revision

The last-eight-layer unfreeze and zero-weight/0.5-bias head proposals are withdrawn. All 35 model-engine/config files remain byte-identical to the 1K parent. The recipe inherits SAO unchanged.

The new PI module serializes exact before/after workspace hunks and bounded static context. Code capsules repeat only after code changes; completed-tool status is eligible per generation. Explicit omissions and a causal quota preserve all Actor tokens. Strict lossless tool-call split matching handles the known SDK history transformation.

Completed observations are journaled at the proxy incoming-message boundary instead of adding SDK callbacks. These observations are already Actor-visible. Test freshness is unknown on arrival and stale after observed code changes; reported test text is not a verifier verdict. PI collection executes no extra tests.

Trainer changes are limited to PI view construction, local audit persistence and checkpoint engineering. See vendor_overrides/trainer_delta_from_1k.patch for the compact diff. Exact archived inputs and the versioned builder reconstruct gather maps. Resume attempts use independent output directories.

40 CPU tests, real Harbor/scripted-generation integration, full launch-command comparison and runtime SHA verification passed. No 9B distributed update, full distributed checkpoint roundtrip, formal training or effectiveness evaluation ran for this revision. These remain explicit acceptance requirements.

The original 1K source is unchanged. Backups, failed attempts and old experimental assets are retained. Git excludes runtime artifacts, weights, credentials and unrelated original-workspace files.
