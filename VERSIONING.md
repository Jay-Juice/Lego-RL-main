# Dynamic PI research version

User authorization: 2026-10-28, an independent copy, unchanged PI budgets and SAO
recipe, iterative diagnostics, conditional fresh training only after admission.

Repository: https://github.com/Jay-Juice/Lego-RL-main.git
Branch: codex/icps-dynamic-state-20261028
Parent reviewed ICPS archive: 823ac025303c3e5b6a829d326edce0a5aa5f127b
Local Git worktree: versioning/icps-dynamic-state-20261028
Source authority: experiments/icps_dynamic_state_v1_20261028

The old ICPS experiment and its branch are preserved. This candidate currently
has a pure input selector and CPU diagnostics, not an accepted online runtime.
The inherited start_full97.sh is disabled (exit 78); inherited preparation
scripts are references, not supported launch commands. No new training has run.

Track reviewed source, tests, admission criteria, aggregate results and hashes.
Exclude model weights, datasets, raw trajectories, private labels and captures,
logs, caches, credentials, deployment evidence and unrelated files. A clone
needs the already pinned private offline environment; do not install or modify
shared dependencies. All 607 historical tasks are development, not a new test
set. Development labels are inaccessible to the generator via Landlock.

Recurring maintenance may push only reviewed committed changes on this branch.
Do not stage unknown files, change main, force-push, merge or launch training
as part of version maintenance. A draft PR is a review record, not approval to
train. ADMISSION_PLAN.md governs the separate conditional training decision.
