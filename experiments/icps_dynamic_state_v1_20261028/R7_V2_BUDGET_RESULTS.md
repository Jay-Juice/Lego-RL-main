# R7 historical V2 budget ablation

Historical V2 is2048tokens per repair state: code1920 plus execution128, versus current development W0cap1024. The actual repair serializer has these independent limits, so generic/reproduction-shell1024 values are not the effective V2repair cap. This is a budget-only study of currentcodewindows, not a replay of V2information content or its training performance.

Increasing the current fixed8window allocator to1920/2048 improves development coverage without observed any/full regressions. Any272/366(74.32%)->284/366(77.60%) for BOTH larger caps,12gained0lost,+3.28pp, exploratory repo95%CI[+1.53,+5.11]pp. Full-all238/366(65.03%)->266(72.68%) at1920 or270(73.77%) at2048:28/32gained0lost, respectively+7.65ppCI[+4.94,+10.82] and+8.74ppCI[+6.00,+11.78]. Targetlines935->1053/1063. The extra128tokens from1920to2048 add4full tasks in aggregate and10targetlines, with no aggregate any-hit count increase.

Cost fails the predeclared low-construction-overhead criterion. Mean offlineconstructor1.652->3.246/3.445s (+96.51%/+108.54%), median1.689->3.097/3.275, P952.678->6.233/6.830. Meanactualtokens998.57->1741.31/1829.83 (+74.38%/+83.24%). Targetline density2.573574->1.683031/1.619400 (-34.60%/-37.08%). Current1024already uses97.52%of cap onaverage;2048uses89.35%onaverage andmedian2039tokens. Largerbudget improves absolute target evidence and completeness, but not informationdensity or cheapconstruction. No extra retrieval/modelcalls were added; more repeated exacttokenization/contextgrowth increases constructorwork. ProductionCritic/trainingcost remains unmeasured.

Loss categories show why the gain saturates: candidateabsence23and no-target-entity-selected45 unchanged; selected-entity/wrong-region26->14 at bothlargercaps. Thus additionalcontext resolves12of26within-entity misses, while68misses remain in candidate/selection stages. Candidate343/366=93.72%unchanged. This directly supports a budget contribution and a separate entity-selection bottleneck; it does not prove a universal cap or an achievable100% result.

Keep1024/8as current practical baseline under the user's lowlatency/density preference. Retain1920/2048only as higher-completeness development comparators; do not deploy automatically. Any future largerbudget use first needs cheaper equivalent construction and better entity/windowrelevance, followed by freshindependent/dynamic/episode/Criticcost validation. This study is607reuseddevelopment inputs/366mapped/77repos, not independentgeneralization orRLbenefit. RuntimeR6 remains192/128/4096 and trainingdisabled.

## Historical budget

V2 formal configuration and actual repair serializer agree on2048per state: code capsule1920(diff1408,ASTcontext384,header/footer128) plus executionstatus128. The repair branch does not read the generic PI_MAX_TOKENS_PER_STATE override; old reproduction-shell1024 is not proof of a1024repair cap. Builder can omit identical code capsules while retaining status.245760Critic sequence minus73728Actor reserve gives172032PI sequence allowance, not actual usage or R6episode4096. See reports/V2_BUDGET_SOURCE_R7_REVIEW.json with original sourceSHA; env/serializer Windows andA800 hashes exact.

This experiment borrows1920code or2048fullstate caps for currentcode/metadata only, no V2execution/test observations. Samepassage24/8slots/proposals/scores/shortlist8/continuousgrowth, onlycapguard/fallbackguard widened in separatedevelopment module. No runtimechange.

## Coverage and density

| Arm | Any /366 | Full-all /366 | Target lines /1320 | Mean tokens /607 | Target lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| control1024_8 | 272 | 238 | 935 | 998.57 | 2.574 |
| fast1920_8 | 284 | 266 | 1053 | 1741.31 | 1.683 |
| fast2048_8 | 284 | 270 | 1063 | 1829.83 | 1.619 |

## Constructor time

| Arm | Wall mean / median / P95 (s) | CPU mean (s) | Mean tokenizer misses | Median paired wall ratio |
|---|---:|---:|---:|---:|
| control1024_8 | 1.652 / 1.689 / 2.678 | 1.652 | 1443.7 | 1.000 |
| fast1920_8 | 3.246 / 3.097 / 6.233 | 3.246 | 1945.4 | 1.867 |
| fast2048_8 | 3.445 / 3.275 / 6.830 | 3.445 | 1991.4 | 1.967 |

## Paired comparisons and loss

| Arm vs control | Any gained/lost | Any delta pp [repo95%CI] | Full gained/lost | Full delta pp [repo95%CI] |
|---|---:|---|---:|---|
| control1024_8 | 0/0 | +0.00 [+0.00,+0.00] | 0/0 | +0.00 [+0.00,+0.00] |
| fast1920_8 | 12/0 | +3.28 [+1.53,+5.11] | 28/0 | +7.65 [+4.94,+10.82] |
| fast2048_8 | 12/0 | +3.28 [+1.53,+5.11] | 32/0 | +8.74 [+6.00,+11.78] |

| Arm | Visible | Candidate absent | Entity not chosen | Chosen entity, wrong region |
|---|---:|---:|---:|---:|
| control1024_8 | 272 | 23 | 45 | 26 |
| fast1920_8 | 284 | 23 | 45 | 14 |
| fast2048_8 | 284 | 23 | 45 | 14 |

All607inputs reused development;366mapped/77repos define changed-line coverage denominator. Candidate343fixed. Any-hit means at leastone targetchangedline;full-all means all mapped targetlines, notsemantic sufficiency. Density is targetlines/1000actualPI tokens over366; meantokens over607. Repo4000bootstrap intervals are exploratory/unadjusted, no independent orRL admission.

7local+7Linux contracts;29inputSHA/bashsyntax pass;607exact current1024control replays. ActualQwen cap/roundtrip/whole-source-lines/nonoverlap for every output.16existinglabel/score paths denied perworker; alloutputs frozen before score and aggregate-only diagnosis.4CPUworkers, fresh perarm/task caches and rotated order. Constructor includes fresh proposal/selection/expansion, excludes initialretrieval/sourceI/O/import/tokenizerinit/Critic; no extra retrieval/model calls. No production latency claim.

Queue logs/v2_budget_r7 exit0; privateinputs/IDs/percaseoutputs remainremote; only aggregate/freeze/diagnostic downloaded. Frozen7/runtime192/128/4096unchanged; noGPU/model/optimizer/training/checkpoint. No active job. Original failures from earlier studies preserved.

AGGREGATE.json SHA 3a01ffe435736374dc849940bb724be05a7a74193f28e1a9c971bc5bd3defcea
FROZEN.json SHA cbb8c4b32c5b5870aa9be7121a4eca88b71c46b80fc8532b94d39f1080b9c9a3
LOSS_DECOMPOSITION.json SHA 5700c5a47a68ef3cebae48bd2385cbd7b981e283448b18d938ea14666c2bfc78

## Executed deployment and queue commands

Windows source: D:/ai project/RL学习/Lego-RL-main; WSL source: /mnt/d/ai project/RL学习/Lego-RL-main; SSH host:A800; remote project:/media/ubuntu/D1/zsj/Lego-RL-main.

```powershell
wsl --exec rsync -anvzc --files-from='/mnt/d/ai project/RL学习/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/.deployment/v2_budget_files.txt' -e /mnt/c/Windows/System32/OpenSSH/ssh.exe '/mnt/d/ai project/RL学习/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/' A800:/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028/
```

Reviewed7files; samecommand with-avzc deployed them. Remote29SHAinputs andbash-npassed.

```sh
cd /media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028
sha256sum -c validation/V2_BUDGET_R7.sha256
bash -n ops/v2_budget_r7.sh
screen -dmS pi-v2-budget-r7 bash ops/v2_budget_r7.sh
```

Queue exit0/state complete_development_only,7Linuxcontracts pass,607outputs then separate scoring/diagnosis. Existing source AST invalid-escape SyntaxWarnings remain in generation logs; assertions and queue completed. A read-only progress command initially used unsupported tail shorthand; corrected to tail-n1, with no experiment interruption or source change.
