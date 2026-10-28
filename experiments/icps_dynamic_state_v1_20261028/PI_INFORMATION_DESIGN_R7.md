# PI information design: next revision, R6 baseline preserved

User direction on 2026-10-28: prioritize real GPU validation or substantive PI
information design; stop expanding generic launch/dependency checks as the main
research output. Disk was subsequently cleared and the fresh resource check passed.

A direct call to the frozen R6 candidate selector on three new synthetic source
pairs reproduced these candidate-level omissions. No confirmation examples,
labels, model calls, tokenizer coverage or RL measurements were used.

| Synthetic change | Frozen R6 selection | Missing observation |
| --- | --- | --- |
| Add new.py with first(x): return x+1 and second(x): return x-1 | first plus unchanged anchor | second is never offered, despite a free third candidate slot |
| Change module LIMIT=10 to LIMIT=20 above compute(x): return min(x,LIMIT) | compute only | changed constant line lies outside every selected entity |
| Change @cached(10) to @cached(20) above compute | compute only | decorator lies before the selected def-line range |

The causes are precise: dynamic_candidates chooses one smallest entity per diff
interval, so a whole added file collapses into one entity; parse_file indexes only
function/class ranges; function ranges begin at def, excluding decorators. These
are input-representation omissions, not proven historical training bugs or measured
RL regressions. Candidate omission does not quantify final tokenizer-level coverage.

Proposed R7 experiment, kept separate from frozen R6:

1. Assign each changed source span to its smallest enclosing source unit, keeping
   all distinct sibling units before ranking. Do not select one entity for an entire
   multi-entity diff interval. Keep the existing maximum three emitted windows.
2. Extend source units to decorator spans and module-level executable statements
   (assignments/imports). Their exact current-source coordinates and kind must be
   explicit; do not invent a function identity for them or add semantic fix claims.
3. Under the same 128-token update cap, prioritize distinct changed units and their
   minimum coherent context before adding unchanged issue anchors or expanding a
   selected window. Initial 192 and episode 4096 caps remain fixed. Preserve retry,
   causal timing, rollback, unknown/limited and whole-window omission semantics.
4. Measure changed-unit availability, emitted changed lines, per-unit context,
   metadata/token share and useful changes retained before budget exhaustion. Do not
   optimize for emitting more lines indiscriminately. Compare real Qwen-tokenized
   outputs to R6 on synthetic cases and the existing development cohort only.

Run the multi-entity correction separately from module/decorator units so their
benefits and losses can be attributed. Initial candidate recall and caller/callee
context are later hypotheses; do not add them simultaneously without evidence.
Any method change requires its own freeze and genuinely independent confirmation;
the R6 confirmation cohort must not be reused to select or tune R7. R6 stays the
GPU probe baseline. Native training recipe/head/freeze/reward/filter are unchanged.

No R7 runtime implementation, deployment, new coverage claim or model update has
been made. Resource readiness now permits completing the existing disposable GPU
probe path; its remaining launch implementation must be finished without treating
this design note or a resource snapshot as launch approval.

## Development budget/pool evidence after human budget authorization

The six-arm W0 factorial is implemented separately and complete; see R7_BUDGET_RESULTS.md. It is not a deployment of the changed-unit design above. Pool3/256 improves visible171->179 and full105->128 on366 development targets. Pool6 improves candidate242->282 but reduces visible hits at every matched cap. Prioritize candidate-to-window ranking (retrieval prior vs local window utility) rather than simply doubling candidates or budget. Keep module/decorator and multi-unit dynamic corrections separate. No R6 confirmation reuse, no runtime budget change, no transferred GPU/independent-admission claim.

## Window research outcome

Predeclared seven-arm development run is complete (R7_WINDOW_RESEARCH_RESULTS.md). At the same256 cap, ordinal retrieval prior and a same-entity window-repeat penalty improve task coverage179->197 with essentially unchanged mean tokens. The improvement is breadth: full-target only128->130 and target-line density only+0.37%. Rank-prior-only188/full137 gives a more balanced point estimate and+4.93% target-line density, but its coverage CI crosses zero. Whole short-statement proposals and no-expansion compression do not jointly improve objectives. Keep diverse6/rank6 as development comparators; next focus is coherent context retention under cross-candidate diversity. No runtime integration or independent confirmation; module/decorator/dynamic-unit proposal remains separate and unimplemented.

## Candidate retrieval evidence

R7_CANDIDATE_RESEARCH_RESULTS.md records four fixed retrieval hypotheses at unchanged256/max3window allocation. Pool12 raises candidate recall282->308 but final hits197->195. Symbol/signature fusion306candidate/200visible/128full has only+3netvisible and a repo interval crossingzero; no promotion. File diversity and static neighbors do not outperform. Scorer-only current-source/entity ceilings are366/363of366 exact-mapped development tasks, so module/decorator omissions explain only a small part of this W0 subset. This does not negate constructed dynamic omissions. Prioritize joint candidate/window relevance using source-only evidence and coherent context; do not claim more retrieval or shorter code alone improves PI. No confirmation tuning or runtime changes.

## Latest R7: joint budget/window experiments complete; no robust promotion

Two actualQwen development experiments completed exit0 on607inputs/366exactmapped/77repos. Seven-arm joint global-objective beam experiment loses coverage/full/density in all4newarms; symbols12/256 visible200->144,full128->71. Post-score diagnostic shows548/607higher heuristic scores, including62/65lost visible hits: objective misalignment, not proof of individual-feature cause. Diagnostic missing-metric exit1 and CRLFmanifest failure retained, corrected aggregate execution exit0; generation/scoring unchanged.

Six-arm same-score lookahead follow-up preserves original proposals/utility/residual expansion; only selection uses width4 approximate search with greedy incumbent. Base6/256 visible197->195/full130->125; symbols12/256 stays200/128,density+1.29%; symbols12/384 visible208->209/full170->173,density+3.91%, but visible repoCI[-1.03,+1.34]pp and full[-0.29,+2.12]pp include0. No reliable coverage breakthrough. Budget-only original symbols12 256->384 gives200->208visible/128->170full at+46.41%mean tokens and-14.54%density. Retain original comparator; do not deploy new variants.

Fixed symbols12 candidate ceiling306/366=83.61%, observedbest209/366=57.10%(209/306candidate conversion68.30%). Source-union99.18%is an oracle availability ceiling, not token-feasible coverage. Next bounded study: constrained-window budget feasibility diagnostic followed by better relevance calibrated on repository-separated development; labels never enter generation, any new candidate needs fresh independent evidence. No near100claim. See R7_JOINT_ALLOCATION_RESULTS.md and joint/lookahead review+aggregate reports. Joint8local/8Linuxsynthetic contracts,followup4/4;607exactcontrol replay each,6/7Landlockdenials/shard,allgenerationfrozenbeforelabels. Frozen7 rehashed exact; runtime/R6confirmation unchanged. No GPU/model/optimizer/training this round; no jobs or monitor remain.

## Latest R7: candidate recall93.72%; final-window ranking remains main bottleneck

logs/recall_windows_r7_r2 exit0 on607seen development inputs/366exactmapped/77repos, actualQwen6arms. Saved symbols12baseline306candidate/200visible/128full at256. Append-only symbols24 gives327/202/129. Full-body128word passage/stride64 retrieval with3channelRRF and originaltop3anchors gives343/205/134,mean250.01vs249.73tokens,density6.031vs5.954(+1.30%). Candidate37gained0lost,+10.11pp(repoCI[+6.98,+13.29]);final7gained2lost,+1.37pp(repoCI[-0.23,+2.89])notrobust. Unforced-prefix free24 retains343candidate hits but final186/123at256,198/162at384; reject as joint utility improvement. Keep anchored passage24 as next development retrieval comparator, not runtime promotion.

Original60candidate misses:3no parsed target entity;57ranked beyond12 (21at13-24,16at25-48,9at49-96,11at97+ in fixed-prefix canonical expansion).41alreadyhave targetfile amongcandidatefiles,19do not. Post-freeze window diagnostic exit0: passage24/256205visible,23candidateabsent,9no hitting seed,129fitting hitting seed not selected,0standalone-budget-blocked. Label-informed actual-or-single-window witness334/366=91.26%does NOT mean achieved coverage or semantic/fulltarget sufficiency; not globalupperbound. Next priority window relevance with anchors/context, not blanket budget increases. R6confirmation untouched.

R1baseline assertion exit1 retained: oldheaderBM25 set iteration yields floating near-tie ordering; fresh old=new but savedpositions9/10swap. R2preserves savedbaseline/prefix, validates identities/sourcehashes/coordinates, canonicalizes newheaderquery and fixesprocesshashseed. Local7/Linux7contracts inclcrossprocessseeds;607exact256payloadreplays,8actualLandlockdenials/shard;allgenerationfrozenbeforelabels. No prior metrics invalidated/no case-score tuning. See R7_RECALL_WINDOWS_RESULTS.md and RECALL_WINDOWS_R7_REVIEW.json. AggregateSHAc9b4320767e9dfda12e17e53573c0f7f92d155c86f6fd73903e7f508c73b63b6,diagnostic5575bcd833162f8d667e6c965e3b4c22c58e4a569be93b0d00fba9d665926096. Frozen7/runtime unchanged; no newGPU/model/optimizer/training; nojobs/monitorremain.
