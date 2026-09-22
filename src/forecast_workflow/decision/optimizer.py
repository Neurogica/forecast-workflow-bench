"""Shared marginal-forecast optimizer with target coverage validation."""

import numpy as np
import pandas as pd

from forecast_workflow.decision.contract import GRID, hourly_cost, optimize, realized_loss
from forecast_workflow.decision.units import capacity_units
from forecast_workflow.forecasting.quantiles import LEVELS


def optimize_marginals(samples, weights, contract):
    scale = capacity_units(contract)[0]
    grid = np.asarray(capacity_units(contract)[1])
    if not np.isfinite(scale) or scale <= 0 or not np.allclose(grid, GRID * scale):
        raise ValueError("Unsupported capacity grid or scale")
    cost = hourly_cost(np.maximum(np.asarray(samples), 0) / scale, weights, contract["terms"])
    indices = optimize(cost, contract["terms"])
    hours = contract["terms"]["block_hours"]
    return dict(
        submission=dict(
            decisions=[
                dict(decision_id=f"b{i:02d}", value=float(grid[k]))
                for i, k in enumerate(indices[::hours])
            ]
        ),
        expected_normalized_loss=realized_loss(cost, indices, contract["terms"]),
        interpretation="Exact grid/ramp optimization conditional on supplied marginal "
        "forecast approximation. Expected loss is not realized performance or hindsight.",
    )


def plan_packet(packet, contract):
    if packet["hours"] != 1:
        raise ValueError(
            "Hourly marginals required; quantiles of bin means are not hourly marginals"
        )
    times = pd.DatetimeIndex(pd.to_datetime(packet["timestamp"], utc=True))
    target = pd.date_range(contract["target_start"], periods=24, freq="h")
    if not times.is_unique or not times.is_monotonic_increasing:
        raise ValueError("Unique ordered forecast timestamps required")
    indices = times.get_indexer(target)
    if (indices < 0).any():
        raise ValueError("Forecast does not cover the full business target")
    if set(packet["quantiles"]) != {str(q) for q in LEVELS}:
        raise ValueError("The control requires all nine native quantiles, 0.1 through 0.9")
    values = np.asarray([packet["quantiles"][str(q)] for q in LEVELS]).T
    if values.shape != (len(times), 9):
        raise ValueError("Quantile shape does not match timestamps")
    return optimize_marginals(values[indices], [0.15] + [0.1] * 7 + [0.15], contract)
