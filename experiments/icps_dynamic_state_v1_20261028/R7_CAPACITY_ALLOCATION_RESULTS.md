# R7 capacity allocation: coverage increases, density does not

Nine actualQwen arms on607seen development inputs/366exactmapped targets/77repos. Same passage24 candidates (343/366=93.72%), source proposals and marginal scoring. The best observed coverage rises from213/366(58.20%,original384/3) to251/366(68.58%,768/6). Full-all174→212(47.54%→57.92%). Mean tokens366.77→744.86(+103.08%) and target-line density5.106→3.179(-37.73%). This is a developmental breadth/depth tradeoff, not a joint density improvement or a runtime promotion. The768cap is a diagnostic stress point, not a modest proposed default.

## Main result: budget allocation and entity selection are major constraints

With3windows,256→384→512→768 yields205→213→214→223visible tasks. All four budgets leave98tasks with a target-containing candidate but no final window from any such entity. Wrong-region misses fall40→32→31→22. More tokens mostly deepen the selected regions; simply tripling the cap does not select the missing entities. These are aggregate counts, not a claim of per-case identity across every arm.

At the same512cap,6windows improve214→237visible (32gained9lost,+6.28pp,exploratory repo95%CI[+2.68,+10.03]pp). At768,6windows improve223→251 (35gained7lost,+7.65pp,CI[+4.79,+10.88]pp). Three→six slots lower no-target-entity-selected count98→66. This directly demonstrates a breadth bottleneck with the fixed scoring rule. Same cap is not same actual cost:768/3 averages665.51tokens,768/6 averages744.86.

At384,6windows improve any213→225 but full-all174→135; at512,full191→171. More small windows displace context. At768 full209→212, but27gained24lost and repoCI[-2.27,+4.06]pp; no robust same-cap completeness improvement. All intervals are exploratory, unadjusted, reused-development estimates after repeated research, not independent admission.

## All predeclared arms

| Arm | Any task /366 | Full-all /366 | Mean tokens /607 | Target lines /1320 | Lines /1000 PI tokens |
|---|---:|---:|---:|---:|---:|
| base256_3 | 205 | 134 | 250.01 | 550 | 6.031 |
| base384_3 | 213 | 174 | 366.77 | 679 | 5.106 |
| base512_3 | 214 | 191 | 473.76 | 746 | 4.374 |
| base768_3 | 223 | 209 | 665.51 | 803 | 3.389 |
| breadth384_6 | 225 | 135 | 381.25 | 599 | 4.297 |
| breadth512_6 | 237 | 171 | 506.00 | 712 | 3.848 |
| breadth768_6 | 251 | 212 | 744.86 | 863 | 3.179 |
| append512_6 | 236 | 166 | 502.88 | 693 | 3.782 |
| append768_6 | 245 | 180 | 713.65 | 753 | 2.936 |

All607outputs have exactly3or6windows according to the arm. Actual Qwen cap/roundtrip, full-source-line equality and nonoverlap pass. Whole source lines do not guarantee complete semantic/control-flow units. Mean tokens use all607; density uses366exactmapped tasks. Per-arm elapsed times share a per-input exact tokenizer cache, so they are not a fair independent latency benchmark.

Append mode freezes the original256 final windows and rendered prefix, then selects/expands only new windows. At512 it reaches236/166 with31any and32full gains,0loss versus256. At768 it reaches245/180 with40any and46full gains,0loss versus256. The guarantee is relative to original256, NOT to original512/768 (matched-cap comparisons do lose tasks). Append has lower full coverage/density than free6allocation at those caps, so it is only a retention comparator. Keeping old context permanently is itself an allocation constraint.

Against256/3,768/6 gives46any gains0loss (+12.57pp,repoCI[+9.48,+15.81]pp) and78full gains0loss. Its density is nevertheless47.29%lower than256. Do not call this more efficient information selection.

## Aggregate loss decomposition

| Arm | Visible | Candidate absent | No target entity chosen | Target entity chosen, wrong region |
|---|---:|---:|---:|---:|
| base256_3 | 205 | 23 | 98 | 40 |
| base384_3 | 213 | 23 | 98 | 32 |
| base512_3 | 214 | 23 | 98 | 31 |
| base768_3 | 223 | 23 | 98 | 22 |
| breadth384_6 | 225 | 23 | 66 | 52 |
| breadth512_6 | 237 | 23 | 66 | 40 |
| breadth768_6 | 251 | 23 | 66 | 26 |
| append512_6 | 236 | 23 | 63 | 44 |
| append768_6 | 245 | 23 | 63 | 35 |

At the previous384/3point,130candidate-containing tasks are missed:98lack a selected target entity and32choose the entity but the wrong region. Candidate recall does not identify the exact correct window. The best768/6still leaves66entity-selection misses,26wrong-region misses and23candidate misses. Candidate-to-final conversion is251/343=73.18%, still far from100%.

First target-containing candidate ranks across343tasks:242at1-3,40at4-6,32at7-12,29at13-24. The smallest target-containing entity is1-10lines in159tasks,11-30in105,31-100in55,101+in24. Large entities contribute but do not explain every failure. Original3-window allocation selects ranks13-24 only9distinct-rank/task occurrences across366tasks;6-window allocation117. These occurrence counts can exceed task counts and are not hits. They describe the ranking bottleneck, not causal attribution to a single score factor.

Previous scorer-only diagnosis found129unselected hitting seeds that fit alone at256; this does not prove all correct contexts fit simultaneously or that a label-free selector can recognize them. Current93.72%candidate recall is a ceiling for this fixed candidate pool, not100%availability. Do not tune on R6confirmation or use label-selected windows as PI.

## Decision and bounded next direction

Retain512/6 as a lower-cost breadth comparator and768/6 as a capacity diagnostic, plus original384/3/protect2 depth comparators. No deployed budget/window-count changes. Neither blind budget increases nor permanently protecting all old context solves relevance. Next useful work is a fixed offline issue/code relevance signal that can promote correct entities and choose precise regions at512orless, evaluated with repository-separated splits and explicit completeness/density constraints. That semantic ranker is not implemented in this experiment. Further cap-only inflation is not the main recommendation.

## Validation, failures and provenance

Generation completed607x9 frozen outputs with6local+6Linux contracts,607exact replays for EACH prior256/384control and11actualLandlocklabel/previous-score denials per shard. Four source-only CPU workers; no R6confirmation, model/GPU/optimizer/training. Original queue exited1 during scoring because the new retention assertion indexed changed-target metrics on rows without mapped exact labels. All607frozen outputs were already complete. Original source/queue retained.

Separate capacity_score_r2 checks metric eligibility consistently, handles ineligible rows explicitly and still rejects any real retention loss. Four local+fourLinux contracts pass; corrected scoring and loss diagnostic queue exits0. A first local wrapper import of Linux resource failed before tests; scoring-only import moved inside main, oldsource/failure retained. No algorithm, cohort, generation or scoring formula change. See SCORING_REPAIR.json and archive/r7_capacity_score_eligibility_failure. No completed generator rerun. Windowsbackup archive/r7_before_capacity_allocation preserves state/docs.

Windows authoritative source → WSLrsync dryrun/review/sync/SHA → bash ops/capacity_allocation_r7.sh → bash ops/capacity_score_r2.sh.21initialsource inputs,3scorerrepair and2diagnosticmanifest entries pass. Only4publicaggregate/freeze/repair reports downloaded; private source/IDs/labels/scores remain remote. Frozen7/runtime unchanged. No active job remains. Formal start_full97.sh remains exit78.

AGGREGATE SHA 68a20273c6b2ef287663382201382b60ad242467b32a1bb607586c06857dbeee
FROZEN SHA 4484def3169a9696831e8fee3988cb2a99eb0037b26a76bd61385bdc03f96244
LOSS_DECOMPOSITION SHA 31956cdc342c0f49518a7f1478f32c2eff9528e9e7330c28eccdde3fbf4edcce
SCORING_REPAIR SHA 1fd56e0ce6d05d67df5dcc370aa395fbb071f8756b44c142ad7137c5037eabc0
