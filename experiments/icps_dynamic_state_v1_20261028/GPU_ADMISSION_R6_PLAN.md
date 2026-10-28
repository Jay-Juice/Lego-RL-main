# R6 remaining admission: native engine and recipe

This plan follows completed CPU proxy, real cached Harbor, and lifecycle checks.
It is not a GPU result or permission to skip existing admission gates.
The frozen seven generator sources and the tested runtime stay unchanged.

## Preparation and source parity

Create new isolated probe/config files after a Windows backup. Keep the inherited
`start_full97.sh` disabled. Do not run the inherited preparation or launch scripts:
their experiment, paths, PI format, Ray ports, and output namespaces still name
the old experiment. Preserve these reference files instead of silently editing
them into launchers.

Inspect `R/src/verl_patch/pi_gpu_smoke.py` as a reference for real native engine
initialization only. Its hand-written old structural PI records and shared
`logs/gpu_smoke_result.json` output are unsuitable for R6 acceptance. A new probe
must create actual R6 records with the frozen session and real tokenizer, then
exercise the same isolated builder used in the completed proxy checks.

Build a new config from the exact original SAO fresh recipe, unique probe EXP,
output directory and PI format `icps_dynamic_v1`. Resolve all Hydra fields and
compare against the historical baseline, including phase1-20/21-97 packing.
`src/resolve_audit.py` and old `FULL_BASELINE_PARITY_r3.json` are references, not
current evidence. Record every allowed namespace/entry-module/method difference.
Do not copy the old `ICPS_V11_FULL_LAUNCH_CONFIG.env` without reviewing its paths.
The formal future experiment remains freshbase with no checkpoint restore.

Verify native head, freeze patterns, reward/filter/SAO/GAE/loss/optimizer,
batch/mini64, SP8/DP1, actor1/critic2 epochs, LR1e-6/5e-6, warmup20, save10/test0,
full97 horizon, complete checkpoint schema and save-before200GiB guard.
Preserve historical packing and inference/logprob budgets; do not infer these
from deprecated forward fields. Inspect current `formal_packing.py` and the real
native configuration/API rather than relying only on defaults.

## Isolated eight-GPU probe

Before any GPU process: all eight GPUs idle, no current experiment process,
no conflicting service/port, private Ray/TMP/output namespaces, enough disk for
existing reserve, offline model/tokenizer and pinned prepared assets. Do not
pull/build/download or stop other processes. If a resource gate fails, preserve
the failure and wait without lowering it or deleting assets.

Use actual Qwen3.5-9B native SP8 model initialization from base weights and short
synthetic batches with real R6 PI. Compare empty PI to baseline values, verify
finite nonempty PI values, exact Actor tensors and causal gathers, then perform
bounded real Critic and Actor updates using unchanged native losses/optimizer.
Probe updates may exercise both packing phases in explicitly labeled disposable
state; never advance or reuse an old training checkpoint. Check real finite loss
and gradient metrics, head/freeze trainable parameters, and actual eight-rank
execution. Tiny CPU gradients are not a substitute.

Persist source/config hashes and compact aggregate metrics, retain diagnostic
logs remotely, and never save/reuse probe weights or optimizer state. No full
training, rollout reward or verifier is needed for this probe. A synthetic short
update is not proof of full-rollout behavior, RL improvement or bitwise resume.

## Final decision

Only after complete source/Hydra parity, real eight-GPU checks and the original
formal resource gates pass, create the unique fresh formal EXP and enable a
new admission-checked entry. Confirm actual base initialization, first rollouts
and updates after starting; a screen alone is not success. Do not restart a
healthy job. Preserve every old experiment and failed measurement.

Current completed evidence is in `HARBOR_DYNAMIC_R6.json`,
`PROXY_LIFECYCLE_R6.json`, `ONLINE_PROXY_R6_CONTRACTS.json`,
`ONLINE_BUILDER_R6_REGRESSION.json`, and `R6_CONFIRMATION_REVIEW.json`.
A disposable probe and receipt consumer are implemented but have not run on GPU.
The consumer has11 local/11 remote CPU contracts; no production receipt was created.
A reviewed receipt producer, complete native dependency/asset coverage, private Ray
lifecycle and actual eight-rank audit remain required before launch.
See GPU_LAUNCH_GATE_R6_REVIEW.json for the current scope and pending work.

Rank-audit implementation is now connected through probe-only native worker
subclasses. Nine remote CPU contracts pass; no real distributed rank was started.
Thirteen explicitly listed native files match SAO, including worker, loss, reward
and trajectory-filter interfaces. Full transitive source review remains pending.
Use GPU_RANK_AUDIT_R6_CONTRACTS.json for scope. The producer/private-Ray gates and
actual eight-GPU acceptance still remain; these CPU assertions do not admit launch.

Private-Ray lease implementation: eight Linux CPU contracts pass in the R2 queue.
The first queue exited1 on an unrelated older process environment permission error;
its source/manifest and logs are preserved. Start-time-first inspection skips older
processes; newer unreadable candidates still fail closed. A real owned Python child
was detected and exited by stdin EOF. No Ray/GPU was initialized and no signal sent.
The probe now requires explicit local Ray kwargs and holds the native shared flock
through receipt consumption and shutdown. Old config alone fails closed; producer,
complete manifest policy, updated whole-Hydra parity and actual Ray lifecycle remain
pending. Latest manifest: validation/GPU_PRIVATE_RAY_R6_CONTRACTS.sha256. Prior rank
manifest binds the archived probe in archive/r6_before_private_ray.
