# R6 online integration plan, pending independent coverage

This is a source inspection and implementation plan, not an integration result.
Do not change the frozen seven generator files while confirmation is running.
Do not enable training. Implement the bridge only after the independent result
meets the existing primary criterion, or record an explicit revised research
decision without claiming that it passed.

## Observed boundaries in the inherited runtime

1. `src/v11_runtime.py:Capture.capture` builds the initial top3 once, then passes
   only files belonging to those candidates in `v11_context`. This is correct
   for the old fixed-candidate provider but would hide edits in new files from
   R6. Merely changing the serializer import cannot implement dynamic PI.
2. `proxy_fields` reconstructs the old WindowSession and restores only
   previous/remaining/last/retries/exhausted/seen. The frozen R6 session also
   needs initial candidates, bounded previous source, last_facts, last_visible
   and its single retry payload. Substituting the class while retaining the old
   cache schema would lose state or fail. These are private per-session host
   fields, not training records.
3. `runtime/vllm_chat_completion_proxy.py` dispatches only `icps_window_v11`
   and excludes only entities/files/v11_context when forming pending records.
   A new context field requires an explicit exclusion. Otherwise raw source or
   issue text could enter returned metadata/rollout records. `pop_session`
   currently strips only the old private cache key.
4. `runtime/remote_docker.py` selects the old image/provider path by the old
   format. A new opt-in format needs explicit provider dispatch, while keeping
   environment, task image identity, registration and teardown semantics.
5. The builder already handles generic PI records and pre-token gather, but
   its no-partial-window total-limit branch recognizes only repair_state_v2 and
   icps_window_v11. A dynamic format must be explicitly tested there. The
   session's4096 budget and the builder's larger fixed sequence reserve are
   distinct constraints; do not silently merge them or alter either budget.

These are anticipated integration obligations in an inactive inherited copy,
not evidence of failures in the old training or currently frozen CPU selector.

## Narrow bridge design

Add a new host-only provider module and separate opt-in PI format. Preserve
old dispatch and source copies. Reuse the frozen bounded workspace reader and
its stable/limited/allowlist constraints. Deliver the complete bounded current
snapshot to the private R6 session, including noninitial candidate files; never
put it into an Actor request, pending record, audit or returned session meta.
The generator must receive exactly the same snapshot representation as the
confirmed CPU composition; do not introduce prefiltering or new ranking.

Keep one explicit R6 session identity per task/session and preserve every
state-machine field. Prefer a narrow cache owner with deterministic close/pop
cleanup, not a deep-copied global cache or monkeypatch. Bound previous source
by the existing8MiB/1500 files and the reader's per-file limit; measure actual
RSS/CPU and object lifetime rather than assuming byte bounds equal Python RSS.
Tokenizers and raw snapshots must remain outside serialized trajectory data.

The capture belongs immediately before generation under existing session
serialization. Preserve logical-call identity on retries. A new scan on retry
may advance provider sequence, but the same logical id and identical workspace
must return the same payload without charging again; changed retry workspace
must fail closed. Do not derive causality from only numerical scan order.

Preserve SDK normalization/tool-split history checks and record coordinates.
Do not change Actor messages, prompt ids, sampling arguments, response masks,
logprobs or routing. Keep PI out of reward/loss timelines; map critic values to
the exact previous-token positions. Keep A-to-B-to-A visible rollback emission.
No global-seen suppression, future final-length truncation or silent stale PI.

## Acceptance sequence after independent coverage passes

1. Back up the local runtime and add the new bridge with training disabled.
   Hash the unchanged seven sources and inherited SAO/model/optimizer files.
   Compare direct frozen session output with the real provider/proxy output on
   identical snapshots, not only helper calls.
2. Run actual Qwen tokenizer and proxy tests for initial192, update128,
   total4096/exhaustion, new-file candidate visibility, edits, deletion versus
   limited/unobserved, rename, parse failure, rollback, no-op, retries, altered
   retries, late/cross-session requests, closed410 and concurrent identities.
   Inspect pending/final metadata to prove raw files, issue and private cache
   are absent, including failure/teardown paths.
3. Exercise real Harbor containers with harmless scripted actions and actual
   pre-generation captures. No hidden verifier, new task tests or extra reward.
   Show the exact before/after source evidence and cache cleanup. Scripted
   generation remains distinct from an actual Actor rollout.
4. Builder/CPU tests must check same Actor ids/masks/logprobs/routing,
   critic ids and PI masks, causal pre-token gathers, retry/split aliases,
   empty/dropped/truncated rows and explicit no-partial-window limits. Compare
   direct frozen emitted ids with ids actually inserted; a token budget alone
   does not prove this equality. Verify row metrics consume the new schema.
5. On eight idle GPUs run an isolated native SP8 short update under unchanged
   SAO recipe, discard weights and optimizer states, inspect real finite
   value/loss/gradient and gather behavior. Do not call short synthetic testing
   full rollout or bitwise-resume validation.
6. Audit full source diffs and complete resolved Hydra args, including native
   head/freeze and historical packing1-20/21-97. Supply a new EXP/output root,
   enforce freshbase and preserve old launch/save disk gates. No old model
   checkpoint restore, warmup save changes, frequency changes or partial saves.
   Only after all admissions pass may the unique new training entry be enabled.

Independent source coverage is only one gate; it does not establish Critic
utilization, EV improvement or downstream task performance.
