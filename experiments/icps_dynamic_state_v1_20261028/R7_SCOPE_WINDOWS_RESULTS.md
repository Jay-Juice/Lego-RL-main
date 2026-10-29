# R7 scope-local window experiment

Neither scope-local arm meets the joint objective. Retain cached1024/8 original selection; reject scope1024_8 and balanced1024_8 as replacements. No runtime promotion. The class-scope hypothesis was tested rather than assumed: more syntactically localized proposals do not improve relevance selection in this implementation.

Baseline272/366any(74.32%),238full-all(65.03%),935targetlines,998.57mean tokens,density2.573574,meanconstructor1.330030s/P952.148445s. Scope-local243any(66.39%)/221full(60.38%),898targetlines,935.36tokens,density2.688542,mean1.070609s/P951.988183s. It gains8andloses37any (-7.92pp, exploratory repo95%CI[-11.18,-5.00]pp), gains17andloses34full (-4.64pp,CI[-7.95,-1.12]). Balanced241any(65.85%)/219full(59.84%),887targetlines,933.93tokens,density2.661130,mean1.068976s/P951.966204s;7gained38lostany (-8.47pp,CI[-11.60,-5.54]),16gained35lostfull (-5.19pp,CI[-8.62,-1.56]). Both pass timing bounds and raise density by using fewer tokens, but lose absolute targetlines/taskcoverage/completeness. These are rejected tradeoffs, not coverage improvements.

The new post-freeze diagnostic directly identifies a more specific bottleneck. Of366tasks,343have a target-containing candidate interval;333(90.98%ofalltasks) already have at least one actual target-containing seed window that individually fits1024. Baseline94misses partition into23candidateabsence,7no-target-seed,64feasible-target-seed-not-emitted;0are solely targetseed-overbudget. Thus64/94=68.09%ofbaseline missedtasks already had an individually feasible correct source window. This is stronger evidence about ranking/combination loss than simply quoting candidate recall. It does NOT show that every target can jointly fit1024, establish achievable91%coverage without labels, or explain full-all completeness by itself. Three baseline hits arise through context growth despite no target-containing seed, so333-272 is not the64miss count.

Scope-local has330individuallyfeasibletargetseedtasks but only243visible; balanced has335feasibletargetseedtasks (more thanbaseline333) yet241visible. Feasible-seed-not-emitted misses rise64->88/95; no-target-seedmisses7->12/7. Merely increasing proposal breadth or changing ownership boundaries is insufficient.362/366tasks have at leastoneclasscandidate, so the4task no-class stratum is too small for broad subgroup conclusions. These compound policies alter seed signals/cap selection/repetition and expansion boundaries; results do not isolate a single cause. Class-range recall can be broad, but in this cohort most candidate-hit tasks already contain small feasible seeds, so class granularity alone does not account for the gap.

Keep1024budget and existing exactcached constructor. This bounded study is complete; do not sweep its parameters on the same cohort. A stronger issue-to-window relevance model with repository-separated development is a plausible future direction, not a demonstrated improvement or an implemented/approved learned ranker. Offline training and small online scoring could be evaluated for latency, but no extra model/dependency/download/training is introduced here. No near100%claim. All607inputs are reuseddevelopment; R6independentconfirmation untouched. Candidate recall343/366unchanged; frozenR6/runtime192/128/4096 and disabledformaltraining remain unchanged.

## Quality and cost

| Arm | Any /366 | Full-all /366 | Target lines /1320 | Mean tokens /607 | Density /1000 tokens | Mean / median / P95 seconds |
|---|---:|---:|---:|---:|---:|---|
| control1024_8 | 272 | 238 | 935 | 998.57 | 2.5736 | 1.330 / 1.378 / 2.148 |
| scope1024_8 | 243 | 221 | 898 | 935.36 | 2.6885 | 1.071 / 1.055 / 1.988 |
| balanced1024_8 | 241 | 219 | 887 | 933.93 | 2.6611 | 1.069 / 1.042 / 1.966 |

## Paired exploratory comparisons

| Arm | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control1024_8 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| scope1024_8 | 8/37 | -7.92 [-11.18,-5.00] | 17/34 | -4.64 [-7.95,-1.12] |
| balanced1024_8 | 7/38 | -8.47 [-11.60,-5.54] | 16/35 | -5.19 [-8.62,-1.56] |

## Post-freeze availability diagnosis

| Arm | Candidate available | Target seed exists | Target seed individually fits | Final visible | Miss: no candidate | Miss: no seed | Miss: seed too large | Miss: feasible seed not emitted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control1024_8 | 343 | 333 | 333 | 272 | 23 | 7 | 0 | 64 |
| scope1024_8 | 343 | 330 | 330 | 243 | 23 | 12 | 0 | 88 |
| balanced1024_8 | 343 | 335 | 335 | 241 | 23 | 7 | 0 | 95 |

Diagnostic target knowledge is used only after generation freezes. An individually affordable target seed does not imply that all target seeds jointly fit or that a label-blind selector can identify it. Expansion can reach a target line not present in seed union. This is not an achievable oracle coverage claim. Per-case evidence remains remote.

607 reused development inputs; changed-line metrics use366mapped tasks/77repositories. Any-hit means at least one target changed line; full-all means every mapped target line, not semantic sufficiency. Candidate recall remains343/366. Density counts target lines per1000actualPI tokens over366; mean tokens over607. Bootstrap intervals are exploratory on adaptively reused data, not independent confirmation or RL evidence.

All three arms use fixed passage24/1024tokens/8windows, same candidate rank prior and cost scoring. New scope arms partition class candidates into methods and residual contiguous gaps, retain original candidate identities, bound seed count to36per candidate, apply repetition penalty by source scope, and prevent context growth across scope boundaries. Balanced arm round-robins methods' seed lists before the36cap. This compound change cannot isolate a single causal component. Class gaps retain source text; syntactic ownership is not semantic relevance or complete-program correctness. Non-class/nested-function handling remains described in source. No extra repository retrieval, neural reranking or runtime changes.

8local and8Linux contracts passed.35inputSHA/bashesyntax verified;607control outputs exactly replay frozen fast1024/8. ActualQwen token cap/roundtrip/whole-source-line/nonoverlap checks pass.18existing label/prior-score paths denied perLandlock worker. Alloutputs frozen before scoring and aggregate diagnosis. Queue logs/scope_windows_r7 exits0. No GPU/model/optimizer/training or testcheckpoint. Frozen7 unchanged, runtime192/128/4096 unchanged, training entry remainsdisabled.

Fresh per-arm/task caches, rotated order over4CPUworkers. Timing includes scope/proposal construction and exact cached/batched tokenization; excludes initialretrieval/I/O/import/tokenizerinit, separate diagnosis and Critic/trainingcompute. Thus this measures offline constructor cost, not end-to-end training latency. Failed/negative arms retained without deployment.

## Deployment

Windows authority D:/ai project/RL学习/Lego-RL-main, remote /media/ubuntu/D1/zsj/Lego-RL-main, SSH A800.

```powershell
wsl --exec rsync -anvzc --files-from='/mnt/d/ai project/RL学习/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/.deployment/scope_windows_files.txt' -e /mnt/c/Windows/System32/OpenSSH/ssh.exe '/mnt/d/ai project/RL学习/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/' A800:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/
```

Reviewed7filepreview, then samecommand with-avzc. Remote:

```sh
cd /media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
sha256sum -c validation/SCOPE_WINDOWS_R7.sha256
bash -n ops/scope_windows_r7.sh
screen -dmS pi-scope-windows-r7 bash ops/scope_windows_r7.sh
```

Only aggregate/frozen/diagnostic reports downloaded after exit0; no private task inputs, per-case labels, model or checkpoint transferred.

AGGREGATE.json SHA 02f815c93faabb058f0b576ab5b7814bcb8c769a240ac35f4adacf3102e08d60
FROZEN.json SHA 8b8c0b9282271e4441a0f384ae790dc6187bb5fc740f05d2dcd04d417af7fa44
LOSS_DECOMPOSITION.json SHA fc485f82c51add0d9c56bfc9c7507d624d53b6739643cce400100caadf8b2db0
