"""Strict independent submission validation for the flexible procurement candidate."""

import numpy as np

from forecast_workflow.decision.contract import GRID, hourly_cost, optimize, realized_loss
from forecast_workflow.decision.units import capacity_units


def grade(submission, contract, actual):
    terms = contract["terms"]
    cost = hourly_cost(np.asarray(actual)[:, None] / capacity_units(contract)[0], [1.0], terms)
    blocks = 24 // terms["block_hours"]
    # Larger than any valid grid action, including every possible change fee.
    invalid_loss = float(
        cost.max(axis=1).mean() + terms["adjustment"] * (GRID[-1] - GRID[0]) * (blocks - 1) / 24 + 1
    )
    loss, valid, indices = invalid_loss, False, None
    try:
        decisions = submission["decisions"]
        ids = [d["decision_id"] for d in decisions]
        if len(ids) != blocks or set(ids) != {f"b{i:02d}" for i in range(blocks)}:
            raise ValueError("All block IDs required exactly once")
        by_id = {d["decision_id"]: d["value"] for d in decisions}
        if any(isinstance(v, (bool, str)) for v in by_id.values()):
            raise ValueError("Capacities must be JSON numbers")
        values = np.asarray([by_id[f"b{i:02d}"] for i in range(blocks)], dtype=float)
        menu = np.asarray(capacity_units(contract)[1])
        match = np.isclose(values[:, None], menu[None, :], atol=1e-6, rtol=1e-9)
        if not np.isfinite(values).all() or not np.all(match.sum(axis=1) == 1):
            raise ValueError("Capacity outside declared grid")
        indices = np.repeat(match.argmax(axis=1), terms["block_hours"])
        loss = realized_loss(cost, indices, terms)
        valid = True
    except (KeyError, ValueError, TypeError, IndexError):
        pass
    oracle = realized_loss(cost, optimize(cost, terms), terms)
    return dict(
        valid=valid,
        normalized_business_loss=loss,
        hindsight_gap=loss - oracle,
        interpretation="Hindsight includes forecast uncertainty, not just reasoning "
        "error. Invalid submissions are worse than any feasible action.",
    )
