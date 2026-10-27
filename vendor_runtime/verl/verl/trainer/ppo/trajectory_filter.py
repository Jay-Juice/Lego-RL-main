# Copyright 2025 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Trajectory termination taxonomy + filter.

Single source of truth for how an agentic rollout terminated. The agent loop tags every
trajectory with exactly ONE mutually-exclusive ``termination_reason`` (``TerminationReason``)
in ``extra_fields`` -> ``non_tensor_batch[TERMINATION_REASON_KEY]``; downstream consumers
(this filter, the off-policy diagnostics) only READ it — never re-infer from tensors. One
classification point keeps the pipeline traceable: a trajectory's fate is decided once, with
a descriptive name, where the signals actually live.

``apply_trajectory_filter`` is a pure policy table: rows whose reason is in
``config.drop_reasons`` are neutralized without changing batch shapes:

1. ``token_level_rewards`` of dropped rows are zeroed (no reward signal can leak);
2. their ``uid`` is rewritten to a singleton group, removing them from the GRPO group
   statistics of their siblings (singleton group -> mean=0/std=1, so with a zeroed reward
   the resulting advantage is exactly 0);
3. a boolean row mask is stored in ``non_tensor_batch[FILTER_MASK_KEY]`` so
   ``zero_filtered_advantages`` can zero advantages/returns after any advantage estimator
   ran (belt-and-braces for non-GRPO estimators).

Configured by ``algorithm.trajectory_filter`` (see TrajectoryFilterConfig); disabled by
default. Per-reason counts are logged under ``trajectory_filter/reason/<reason>``.
"""

from typing import Optional

import numpy as np
import torch

from verl import DataProto

FILTER_MASK_KEY = "trajectory_filter_mask"
TERMINATION_REASON_KEY = "termination_reason"


class TerminationReason:
    """Canonical, mutually-exclusive outcome of one agentic trajectory.

    Set ONCE by the agent loop. ``overlong`` covers both length budgets — the model context
    window (prompt overflow mid-rollout) and the training response window (response sliced to
    fit) — because both end with a truncated-but-real trajectory carrying a real verifier reward.
    """

    AGENT_COMPLETED = "agent_completed"      # ran to a normal stop; verifier scored it
    OVERLONG = "overlong"                    # hit a length budget (context window or response window); truncated
    MAX_TURNS_REACHED = "max_turns_reached"  # hit the turn cap
    TIMEOUT = "timeout"                      # agent / verifier wall-clock timeout
    ENV_SETUP_FAILED = "env_setup_failed"    # sandbox/env never produced a usable trajectory (dummy 1-token row)


ALL_TERMINATION_REASONS = (
    TerminationReason.AGENT_COMPLETED,
    TerminationReason.OVERLONG,
    TerminationReason.MAX_TURNS_REACHED,
    TerminationReason.TIMEOUT,
    TerminationReason.ENV_SETUP_FAILED,
)

# Categories whose reward reflects the environment, not the policy -> excluded from training
# by default. Overlong / max_turns_reached are KEPT (real, if truncated, learning signal).
DEFAULT_DROP_REASONS = (TerminationReason.TIMEOUT, TerminationReason.ENV_SETUP_FAILED)


def _rows_without_response_tokens(batch: DataProto) -> Optional[np.ndarray]:
    """Rows whose ``response_mask`` has no valid token, i.e. no model-generated token.

    Structurally unusable rather than a termination outcome: every policy loss is
    masked by ``response_mask``, so such a row contributes no gradient no matter what
    it is worth. Neutralizing it is therefore mathematically free, and it avoids two
    real failures — ``compute_rollout_correction_and_rejection_mask`` raises
    ``"response_mask must contain at least one valid token (1)."`` when a whole
    micro-batch ends up empty, and any per-row mean over the mask divides by zero.

    Returns None when the batch has no ``response_mask`` to inspect.
    """
    response_mask = batch.batch.get("response_mask")
    if response_mask is None:
        return None
    if response_mask.is_nested:
        counts = torch.tensor([m.sum() for m in response_mask.unbind()])
    else:
        counts = response_mask.sum(dim=-1)
    return (counts == 0).cpu().numpy()


def _neutralize(batch: DataProto, invalid: np.ndarray) -> None:
    """Zero reward + singleton-uid the flagged rows and record them for advantage zeroing."""
    if not invalid.any():
        return
    invalid_t = torch.from_numpy(invalid).to(batch.batch["token_level_rewards"].device)
    # 1) no reward signal may leak through the singleton group
    batch.batch["token_level_rewards"][invalid_t] = 0.0
    # 2) remove from sibling GRPO group statistics via singleton uid
    if "uid" in batch.non_tensor_batch:
        uids = batch.non_tensor_batch["uid"]
        for i in np.nonzero(invalid)[0]:
            uids[i] = f"{uids[i]}__filtered_{i}"
    # 3) remember rows for post-advantage zeroing
    batch.non_tensor_batch[FILTER_MASK_KEY] = invalid


def apply_trajectory_filter(batch: DataProto, config) -> tuple[DataProto, dict]:
    """Neutralize trajectories whose ``termination_reason`` is in ``config.drop_reasons``.

    Must run AFTER ``token_level_rewards`` is set and BEFORE advantage computation.

    Args:
        batch: training batch with ``token_level_rewards``, ``non_tensor_batch["uid"]`` (GRPO),
            and ``non_tensor_batch[TERMINATION_REASON_KEY]`` (per-row reason set by the agent loop).
        config: ``algorithm.trajectory_filter`` (TrajectoryFilterConfig / DictConfig / None).

    Returns:
        (batch, metrics): batch is modified in place; metrics carry per-reason counts and the
        dropped total.
    """
    # Structural check, deliberately outside the enable switch: a row with no
    # model-generated token is unusable regardless of policy, and leaving it in
    # crashes the rollout-correction path. Neutralizing it changes nothing for the
    # losses, which are all masked by response_mask anyway.
    empty = _rows_without_response_tokens(batch)
    empty_count = int(empty.sum()) if empty is not None else 0

    if config is None or not config.get("enable", False):
        if empty_count:
            _neutralize(batch, empty)
            return batch, {"trajectory_filter/no_response_token_count": empty_count}
        return batch, {}

    n = len(batch)
    drop_reasons = set(config.get("drop_reasons", DEFAULT_DROP_REASONS) or [])

    # Per-row termination_reason set once by the agent loop. Rows missing it (should not happen
    # now every loop emits it) default to agent_completed, i.e. never dropped — fail safe.
    raw = batch.non_tensor_batch.get(TERMINATION_REASON_KEY)
    if raw is None:
        reasons = np.full(n, TerminationReason.AGENT_COMPLETED, dtype=object)
    else:
        reasons = np.array([str(x) for x in raw], dtype=object)

    invalid = np.array([r in drop_reasons for r in reasons], dtype=bool)
    if empty is not None:
        invalid |= empty

    # Visibility: count every reason seen (whether dropped or kept), plus the dropped total.
    metrics: dict[str, float] = {}
    seen: dict[str, int] = {}
    for r in reasons:
        seen[r] = seen.get(r, 0) + 1
    for reason in ALL_TERMINATION_REASONS:
        metrics[f"trajectory_filter/reason/{reason}"] = int(seen.get(reason, 0))
    unknown = sum(c for r, c in seen.items() if r not in ALL_TERMINATION_REASONS)
    if unknown:
        metrics["trajectory_filter/reason/unknown"] = int(unknown)
    # Counted separately from the reasons above: a row can be both agent_completed and
    # empty, so this does not partition the batch the way termination_reason does.
    metrics["trajectory_filter/no_response_token_count"] = empty_count
    metrics["trajectory_filter/invalid_count"] = int(invalid.sum())
    metrics["trajectory_filter/invalid_ratio"] = float(invalid.mean()) if n else 0.0

    _neutralize(batch, invalid)
    return batch, metrics


def zero_filtered_advantages(batch: DataProto) -> DataProto:
    """Zero advantages/returns of rows flagged by ``apply_trajectory_filter``.

    Estimator-agnostic safety net: a zero advantage contributes exactly zero policy
    gradient regardless of clipping or IS weighting. No-op when nothing was flagged.
    """
    if FILTER_MASK_KEY not in batch.non_tensor_batch:
        return batch
    invalid = torch.from_numpy(np.asarray(batch.non_tensor_batch[FILTER_MASK_KEY], dtype=bool))
    for key in ("advantages", "returns"):
        if key in batch.batch:
            batch.batch[key][invalid.to(batch.batch[key].device)] = 0.0
    return batch
