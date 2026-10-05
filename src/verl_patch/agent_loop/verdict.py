"""Validate binary SWE rewards without importing the training runtime."""

import math
from collections.abc import Mapping


def binary_verifier_reward(verifier_result):
    """Return 0/1 only for an explicit finite verdict; otherwise return None."""
    rewards = getattr(verifier_result, "rewards", None)
    if not isinstance(rewards, Mapping) or "reward" not in rewards:
        return None
    try:
        value = float(rewards["reward"])
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value in (0.0, 1.0) else None
