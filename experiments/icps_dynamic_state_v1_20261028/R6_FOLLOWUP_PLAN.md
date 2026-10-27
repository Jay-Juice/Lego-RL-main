# R6 follow-up: freeze the candidate, then test its composition

R6 is a development selection, not evidence that repeated query terms were the
main bottleneck. Both variants hit171/366; choosing novelty_cost_expand because
its full target105 exceeds102 is an explicitly post-result secondary decision.
Against R4 it gains13 and loses11, with an exploratory cluster interval crossing
zero. Target-line density6.4519 versus6.4462 is effectively unchanged. Do not
describe this as a substantial improvement over R4, or a Critic/RL result.

The W0 six-source freeze is CANDIDATE_FREEZE_R6.json. Preserve the R4 freeze.
Before consuming another independent cohort, build a separate session adapter:

1. Use the frozen R6 cost selector only for initial stable W0 source with no
   status facts. Preserve the verified current-source R4 status path when facts
   require disclosure. No global monkeypatch of the frozen selector.
2. Updates use exactly R4 flow change-priority proposals, status accounting and
   the128 budget. Keep the same current candidate refresh, visible-state dedup,
   rollback, logical retry, session identity and4096 exhaustion accounting.
   This is deliberately a W0 ranking change plus the existing dynamic method;
   do not silently apply a W0 heuristic to changed-line priority.
3. Verify all607 initial outputs against frozen R6, including documenting any
   inputs requiring the explicit status path. If output differs, stop and audit
   before treating the combined candidate as the measured W0 method. Run the
   actual Qwen tokenizer on24 UID-selected capacity-qualified real snapshots
   with constructed addition/edit/delete/rollback/noop/retry events, plus
   cross-session/late/retry-change/exhaustion negatives. Keep oracle labels out.
   Synthetic changes are not actual Actor trajectories or real bug coverage.
4. Only then freeze the complete adapter and a fresh independent task manifest,
   excluding607 development, all220 R4 confirmation and every audited historical
   exposure. Use an inventory rule fixed before scoring, not a result-based
   sample expansion. Remaining tasks may be unseen tasks in seen repositories;
   report that limitation. Do not relabel them as unseen repositories.
5. Evaluate only the frozen combined candidate against old S1. The existing
   independent primary delta>0 and repository-cluster95%lower>0, full-target
   nonregression and unavailable-case accounting remain unchanged. Do not
   revisit220 or continue sampling until significance.

Online provider/proxy/builder, real Harbor, causal gather/Actor invariance,
8GPU short discarded update, full SAO source/dryrun and resource gates are still
mandatory. Training remains disabled. No budget, packing, optimizer, reward or
SAO formula changes are authorized by this plan.
