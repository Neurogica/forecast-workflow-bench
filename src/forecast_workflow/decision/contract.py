"""Flexible capacity procurement with ramp limits and adjustment charges.

The synthetic contract uses real hourly demand. Marginal distributions suffice:
shortage charges are additive over hours; ramps couple actions, not random paths.
"""

import numpy as np

GRID = np.round(np.arange(0.4, 2.001, 0.05), 2)


def hourly_cost(samples, weights, terms):
    samples, weights = np.asarray(samples), np.asarray(weights)
    if (
        samples.ndim != 2
        or samples.shape[0] != 24
        or weights.shape != (samples.shape[1],)
        or not np.isfinite(samples).all()
        or not np.isfinite(weights).all()
        or np.any(weights < 0)
        or not np.isclose(weights.sum(), 1)
    ):
        raise ValueError("Expected 24 finite hourly marginals and probability masses")
    shortage = np.maximum(samples[:, :, None] - GRID[None, None, :], 0)
    priority = np.asarray(terms["hourly_priority"])
    billing = terms.get("billing", "reservation")
    if billing not in ("reservation", "imbalance"):
        raise ValueError("Unknown billing convention")
    surplus = (
        GRID[None, None, :]
        if billing == "reservation"
        else np.maximum(GRID[None, None, :] - samples[:, :, None], 0)
    )
    cost = terms["reservation"] * surplus + priority[:, None, None] * (
        terms["shortage"] * shortage
        + terms["emergency"] * np.maximum(shortage - terms["emergency_buffer"], 0)
    )
    return np.einsum("hsg,s->hg", cost, weights)


def optimize(cost, terms):
    """Exact shortest path on the finite capacity grid, deterministic tie breaking."""
    cost = np.asarray(cost)
    if cost.shape != (24, len(GRID)) or not np.isfinite(cost).all():
        raise ValueError("Invalid hourly cost table")
    hours = terms["block_hours"]
    if hours not in (1, 3, 6):
        raise ValueError("Unsupported commitment duration")
    block_cost = cost.reshape(24 // hours, hours, len(GRID)).sum(axis=1)
    difference = np.abs(GRID[:, None] - GRID[None, :])
    transition = np.where(
        difference <= terms["ramp"] + 1e-10, terms["adjustment"] * difference, np.inf
    )
    values = block_cost[0].copy()
    parents = []
    for block in block_cost[1:]:
        candidates = values[:, None] + transition
        parent = candidates.argmin(axis=0)
        parents.append(parent)
        values = candidates[parent, np.arange(len(GRID))] + block
    index = int(values.argmin())
    path = [index]
    for parent in reversed(parents):
        index = int(parent[index])
        path.append(index)
    return np.repeat(path[::-1], hours)


def realized_loss(cost, indices, terms):
    indices = np.asarray(indices)
    if (
        indices.shape != (24,)
        or indices.dtype.kind not in "iu"
        or np.any(indices < 0)
        or np.any(indices >= len(GRID))
    ):
        raise ValueError("Invalid action indices")
    actions = GRID[indices]
    h = terms["block_hours"]
    if not np.array_equal(actions, np.repeat(actions[::h], h)) or np.any(
        np.abs(np.diff(actions[::h])) > terms["ramp"] + 1e-10
    ):
        raise ValueError("Infeasible commitment")
    return float(
        (
            cost[np.arange(24), indices].sum()
            + terms["adjustment"] * np.abs(np.diff(actions[::h])).sum()
        )
        / 24
    )
