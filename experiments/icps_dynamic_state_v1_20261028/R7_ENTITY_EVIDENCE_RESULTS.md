# R7 entity evidence and exact construction optimization

This bounded experiment achieves an exact construction-cost reduction, but neither new entity-selection rule meets the joint coverage/density/completeness objective. Retain the original1024/8 selection and the new cached1024_8 development implementation; reject entity1024_8 and complement1024_8 as replacements. No runtime promotion or training change.

The cached arm exactly replays all607 complete baseline output dictionaries, including tokens/source maps/windows/semantic hashes. Any-hit remains272/366(74.32%), full-all238/366(65.03%), visible targetlines935/1320, density2.573574targetlines/1000PI tokens, mean998.57tokens. Mean construction time1.643644->1.320374s (-19.67%), median1.699404->1.366917s, P952.683700->2.123874s (-20.86%); median paired time ratio0.8139. Mean unique tokenizer misses remain1443.66 in both arms; the optimized arm averages90.11 backend batches. The combined AST/line/term cache and batch optimization is measured together, not proof that batching alone caused the gain or that fewer source strings were tokenized. No persistent cache or additional retrieval/modelcall.

Whole-unit evidence weighting reaches268any(73.22%)/236full(64.48%),953targetlines,density2.634249 (+2.36%),996.51mean tokens,1.329902s mean. It gains3andloses7any tasks (-1.09pp, exploratory repo95%CI[-2.81,+0.59]pp), gains4andloses6full (-0.55pp,CI[-2.24,+1.21]). Complementary evidence reaches267any(72.95%)/235full(64.21%),951targetlines,density2.627239 (+2.09%),996.75tokens,1.328945s mean;3gained8lost any (-1.37pp,CI[-3.16,+0.34]),4gained7lost full (-0.82pp,CI[-2.66,+1.02]). Both are faster than original control because they share the exact performance changes; neither improves task coverage or completeness. Intervals crossing0 are not evidence of equivalence/noninferiority.

The loss diagnosis rejects the intended selection improvement: no-target-entity-selected45->55/56, while within-selected-entity wrong-region misses26->20; candidateabsence23unchanged. More aggregate targetlines and slightly higher density do not compensate for fewer covered tasks. Candidate-own lexical/identifier evidence with the fixed bounded multiplier is insufficient in this form; this experiment does not establish that all entity-level signals are useless. Preserve the useful rank prior and original choices rather than deploy these weights.

Keep budget1024 and original quality; use the proven exact cached/batched constructor as the next W0 development control. Any future selection research needs a more discriminating issue-to-code relevance signal evaluated on repository-separated development and fresh independent evidence; no learned model or additional parameter sweep was started. All607cases are reused development (366mapped/77repos); no independent generalization, semantic completeness or RL claim. Timing excludes initial retrieval/I/O/init/Critic; the20% constructor improvement is not a20% training speedup. FrozenR6 runtime192/128/4096 and disabled training entry remain unchanged.

## Coverage and density

| Arm | Any /366 | Full-all /366 | Target lines /1320 | Mean tokens /607 | Target lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| control1024_8 | 272 | 238 | 935 | 998.57 | 2.574 |
| cached1024_8 | 272 | 238 | 935 | 998.57 | 2.574 |
| entity1024_8 | 268 | 236 | 953 | 996.51 | 2.634 |
| complement1024_8 | 267 | 235 | 951 | 996.75 | 2.627 |

## Constructor timing

| Arm | Wall mean / median / P95 (s) | CPU mean (s) | Mean tokenizer misses | Median paired wall ratio |
|---|---:|---:|---:|---:|
| control1024_8 | 1.644 / 1.699 / 2.684 | 1.644 | 1443.7 | 1.000 |
| cached1024_8 | 1.320 / 1.367 / 2.124 | 1.320 | 1443.7 | 0.814 |
| entity1024_8 | 1.330 / 1.377 / 2.186 | 1.330 | 1433.6 | 0.810 |
| complement1024_8 | 1.329 / 1.351 / 2.194 | 1.329 | 1435.0 | 0.813 |

## Paired comparisons and loss

| Arm vs control | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control1024_8 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| cached1024_8 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| entity1024_8 | 3/7 | -1.09 [-2.81,+0.59] | 4/6 | -0.55 [-2.24,+1.21] |
| complement1024_8 | 3/8 | -1.37 [-3.16,+0.34] | 4/7 | -0.82 [-2.66,+1.02] |

| Arm | Visible | Candidate absent | Entity not chosen | Chosen entity, wrong region |
|---|---:|---:|---:|---:|
| control1024_8 | 272 | 23 | 45 | 26 |
| cached1024_8 | 272 | 23 | 45 | 26 |
| entity1024_8 | 268 | 23 | 55 | 20 |
| complement1024_8 | 267 | 23 | 56 | 20 |

Four arms use the same 1024 cap, eight windows and passage24 candidate pool. The cached arm resolves the current AST once per invocation, caches source lines and lexical terms, and batches exact full-payload tokenizer calls. It does not assume BPE token counts are additive. Both the original control and cached arm exactly replay every one of the 607 frozen baseline output dictionaries. Cache lifetime is one invocation; no persistent or cross-task/source cache.

The two selection arms retain the original window proposals, score, candidate rank prior, repetition penalty and contiguous expansion. They add a bounded whole-unit evidence multiplier. Evidence comes from candidate-own AST identifiers/attributes/arguments/non-docstring string literals plus path/qualified name, with nested scopes excluded. Query matches are weighted across candidate documents; the complementary arm additionally rewards evidence not represented in previously selected candidate units. This evidence need not be inside an emitted window; it is a selection heuristic, not proof of semantic completeness. See R7_ENTITY_EVIDENCE_PLAN.md for fixed coefficients and acceptance criteria.

607 reused development inputs; 366 exact-mapped tasks from 77 repositories define changed-line metrics. Candidate recall remains343/366. Any-hit means at least one mapped target line; full-all means every mapped target line, not semantic sufficiency. Density is target lines per1000actualPI tokens over366; mean tokens over607. Repository4000-bootstrap intervals are exploratory and unadjusted. No R6 independent confirmation access or per-case label inspection for tuning.

8 local and8 Linux contracts;29 inputSHA and bashsyntax pass. Actual Qwen token-cap/roundtrip/full-source-line/nonoverlap assertions pass for every output.17 existing label/prior-score paths are denied in each Landlock generation worker. All outputs freeze before scoring and aggregate-only diagnosis. Queue logs/entity_evidence_r7 exits0. Existing AST escape SyntaxWarnings remain in logs; assertions and execution succeed.

Fresh caches per arm/task, rotated arm order across4CPUworkers. Timing includes fresh proposal construction, evidence scoring, parsing, caches and batching; excludes initial retrieval/sourceI/O/import/tokenizer initialization and Critic compute. No additional repository retrieval, model or neural reranker. This is offline constructor cost, not measured training latency or RL benefit.

Windows authority, reviewed WSL rsync7-file preview then sync,29SHA verification, and screen -dmS pi-entity-evidence-r7 bash ops/entity_evidence_r7.sh from the remote experiment directory. Only aggregate/freeze/diagnostic reports downloaded; private captures, identifiers and per-case outputs remain remote. Frozen7 and runtime192/128/4096 unchanged; no newGPU/model/optimizer/training/checkpoint. No active job.

AGGREGATE.json SHA e3cb8c71350dd73b83cec005082889e889d370fe0f40a82d56957df61c55b8da
FROZEN.json SHA 06f83735e153863c26956fec159c3eefd029c4e4e58f92d4630b745de3a060a3
LOSS_DECOMPOSITION.json SHA af5660b3b12b405b095c7a42a4e75d63fb19b2ecfb7bf4988783bdaff1d283d1

## Deployment commands

Windows project:D:/ai project/RL学习/Lego-RL-main; SSHhost:A800; remote project:/media/ubuntu/D1/zsj/Lego-RL-main.

```powershell
wsl --exec rsync -anvzc --files-from='/mnt/d/ai project/RL学习/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/.deployment/entity_evidence_files.txt' -e /mnt/c/Windows/System32/OpenSSH/ssh.exe '/mnt/d/ai project/RL学习/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/' A800:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/
```

Preview reviewed7files; samecommand with-avzc performed transfer.

```sh
cd /media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
sha256sum -c validation/ENTITY_EVIDENCE_R7.sha256
bash -n ops/entity_evidence_r7.sh
screen -dmS pi-entity-evidence-r7 bash ops/entity_evidence_r7.sh
```

Verified29SHAinputs,8Linuxcontracts and queueexit0. No inherited launch/preparation/training command executed.
