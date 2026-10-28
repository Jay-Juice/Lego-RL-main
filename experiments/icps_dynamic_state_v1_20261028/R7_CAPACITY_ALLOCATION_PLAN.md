# Budget, slot count and retention intervention (pre-score)

Windows source authority D:/ai project/RL学习/Lego-RL-main; WSL source /mnt/d/ai project/RL学习/Lego-RL-main; SSH A800; remote /media/ubuntu/D1/zsj/Lego-RL-main. Frozen R6/runtime untouched.

User asks why 93.72% candidate recall converts to only 58.20% final any-task coverage, and authorizes coverage research and experimental budget increases. Fix saved passage24 candidates, original source proposals, original diverse6 marginal score and context expansion. No new relevance weights or case-driven tuning. Nine arms:

| Family | Token caps | Max windows | Retained prefix |
|---|---|---|---|
| Original allocation | 256,384,512,768 | 3 | None |
| More seed slots | 384,512,768 | 6 | None |
| Append after original final PI | 512,768 | 6 | Original256 final windows and payload bytes |

The768 cap is a diagnostic stress point (3x256), not a proposed modest default or runtime budget change. More slots are an explicit developmental intervention, not hidden compliance with the runtime max3. Update128/episode4096 and deployed initial192 stay fixed. Extra slots take budget before context expansion. Append freezes original final source intervals; only additional windows expand. This directly tests whether spending all residual budget on the first three windows restricts breadth. At most three extra windows when the baseline filled three slots. Empty baseline uses ordinary bounded fallback.

Prior evidence:343/366 candidates,205visible at256,213at384. A scorer-only prior diagnostic found129 cases with an unselected hitting seed fitting alone; this demonstrates existence, not that all correct evidence fits simultaneously or can be recognized without labels. Do not equate an oracle witness with achievable coverage.

Reuse all607development inputs; metrics on366exactmapped targets/77repos, not independent/new-repository evidence. Freeze all607x9outputs before separate label scorer. Per-file Landlock source-record grants, actual denied label and previous-score reads. No R6 confirmation access or per-case inspection. Actual Qwen tokenization cached exactly per input (returned list copied), full source lines, nonoverlap, roundtrip and caps checked. Reproduce prior256/384 payloads exactly. Append must preserve every old visible source coordinate and hence have zero lost any/full targets; assert in scorer too. No claim of complete semantic units from whole-line preservation.

Compare matched-budget3vs6,3-slot budget curves,append vs free6 and base256. Report paired gains/losses/repository bootstrap intervals, full-all target coverage, target-line density, actual mean tokens, metadata and window/entity counts. Report all arms including negative results. These are exploratory unadjusted reused-development comparisons. No hidden tuning after outcomes. Candidate343 unchanged. Freeze source receipt and hashes. No model/GPU/training; no generic infrastructure expansion.
