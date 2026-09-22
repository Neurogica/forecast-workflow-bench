"""Primary-track MCP server: fixed forecast services and shared decision support."""

import json
import os
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP

from forecast_workflow.decision.classical import classical_forecasts
from forecast_workflow.decision.optimizer import optimize_marginals, plan_packet
from forecast_workflow.decision.units import capacity_units
from forecast_workflow.forecasting.engine import ForecastTools
from forecast_workflow.forecasting.quantiles import LEVELS, QuantileTools

Model = Literal["seasonal_empirical", "chronos_bolt_tiny", "chronos2", "timesfm25"]
TOOLS = [
    "catalog",
    "history",
    "inspect_series",
    "budget_status",
    "quote_forecast",
    "forecast_and_plan",
    "hourly_history_plan",
    "replay_forecast",
]


CLASSICAL = [
    "weekday_empirical",
    "weekly_repeat",
    "all_hour_empirical",
    "calendar_residual",
    "recent_week_empirical",
    "recent_day_empirical",
    "hour_of_day_empirical",
    "level_adjusted_weekly",
]
TOOLS += ["classical_plan"]
Method = Literal[
    "weekday_empirical",
    "weekly_repeat",
    "all_hour_empirical",
    "calendar_residual",
    "recent_week_empirical",
    "recent_day_empirical",
    "hour_of_day_empirical",
    "level_adjusted_weekly",
]


def compact_plan(packet, contract):
    values = np.asarray([packet["quantiles"][str(q)] for q in LEVELS], dtype=float).T
    if not np.isfinite(values).all() or (np.diff(values, axis=1) < -1e-6).any():
        raise ValueError("Finite ordered native marginal quantiles required")
    plan = plan_packet(packet, contract)
    return dict(
        capacity_plan=plan,
        forecast=dict(
            model=packet["model"],
            series_id=packet["series_id"],
            start=packet["timestamp"][0],
            end=packet["timestamp"][-1],
            horizon=len(packet["timestamp"]),
            context_steps=packet["context_steps"],
            hours=packet["hours"],
            unit=packet["unit"],
            representation="Nine hourly marginal quantiles; negative demand clipped to zero.",
        ),
        forecast_budget=packet.get("forecast_budget"),
    )


def make_server(root, as_of):
    contract = json.loads((root / "business_contract.json").read_text())
    log = os.environ.get("FWB_BUDGET_LOG")
    engine = ForecastTools(root, as_of, Path(log) if log else None)
    quantiles = QuantileTools(engine, root / "probabilistic_forecasts.json")
    server = FastMCP("forecast-workflow-compact-decision-support-v2")
    server.add_tool(engine.budget_status, name="budget_status")

    @server.tool()
    def catalog() -> dict:
        """Public series, valid model IDs, forecast timing semantics, and remaining credits."""
        return dict(
            series=engine.catalog()["series"],
            as_of=engine.as_of.isoformat(),
            models=quantiles.capabilities(),
            forecast_budget=engine.budget_status(),
            semantics="Forecasts start one hour after the last visible observation. "
            "Choose horizon to cover every target hour, including the observation gap. "
            "context_steps counts hourly observations. Model IDs exclude tariff suffixes. "
            "Optimizer is free and identical across agents and fixed reference policies. "
            "Expected losses are conditional on each forecast and cannot establish which "
            "model will perform best. Replay only verifies observed historical outcomes.",
        )

    @server.tool()
    def inspect_series(series_id: str) -> dict:
        """Hourly visible-history coverage; no aggregation argument is needed in this track."""
        return engine.inspect_series(series_id, 1)

    @server.tool()
    def history(series_id: str, limit: int = 48) -> dict:
        """Last 1..336 visible hourly observations, for understanding or historical validation."""
        return engine.history(series_id, limit, 1)

    @server.tool()
    def quote_forecast(series_id: str, model: Model, horizon: int, context_steps: int) -> dict:
        """Free quote for forecast_and_plan; horizon 1..336, context within visible history."""
        return quantiles.quote(series_id, model, horizon, context_steps, 1, list(LEVELS))

    @server.tool()
    def forecast_and_plan(series_id: str, model: Model, horizon: int, context_steps: int) -> dict:
        """Buy a forecast and return its optimized capacity_plan.submission for final JSON.

        Select model, horizon and context. Full target coverage is required. Forecasts
        are charged even if too short for a plan; quote first to check affordability.
        Compact output omits raw quantile arrays, never the plan or charged credits.
        """
        packet = quantiles.forecast(series_id, model, horizon, context_steps, 1, list(LEVELS))
        return compact_plan(packet, contract)

    @server.tool()
    def hourly_history_plan(series_id: str) -> dict:
        """Free plan using all visible same-hour observations; returns capacity_plan.submission.

        This is a classical reference with no forecast credits, not a known best plan.
        """
        series = engine._series(series_id, 1)
        target = pd.date_range(contract["target_start"], periods=24, freq="h")
        samples = [series[series.index.hour == t.hour].values for t in target]
        if not samples or min(map(len, samples)) == 0 or len(set(map(len, samples))) != 1:
            raise ValueError("Complete balanced hourly historical marginals required")
        values = np.asarray(samples)
        return dict(
            capacity_plan=optimize_marginals(
                values, np.ones(values.shape[1]) / values.shape[1], contract
            ),
            forecast_budget=engine.budget_status(),
        )

    @server.tool()
    def replay_forecast(
        series_id: str, model: Model, origin: str, horizon: int, context_steps: int
    ) -> dict:
        """Buy a past-only forecast; return observed-window pinball loss and coverage.

        origin must be timezone-aware and at/before as_of. Only observations already
        visible are scored; complete=False means this replay cannot validate its full horizon.
        Forecast credits are charged at the same tariff as forecast_and_plan.
        """
        packet = quantiles.replay(series_id, model, origin, horizon, context_steps, 1, list(LEVELS))
        times = pd.to_datetime(packet["timestamp"], utc=True)
        visible = engine._series(series_id, 1).reindex(times).to_numpy(dtype=float)
        mask = np.isfinite(visible)
        values = np.asarray([packet["quantiles"][str(q)] for q in LEVELS]).T
        loss = None
        if mask.any():
            error = visible[mask, None] - values[mask]
            levels = np.asarray(LEVELS)
            loss = float(np.maximum(levels * error, (levels - 1) * error).mean())
        return dict(
            model=model,
            origin=origin,
            horizon=horizon,
            observed_hours=int(mask.sum()),
            complete=bool(mask.all()),
            mean_pinball_loss_mw=loss,
            forecast_budget=packet.get("forecast_budget"),
        )

    @server.tool()
    def classical_plan(series_id: str, method: Method) -> dict:
        """Free classical forecast and optimized capacity_plan.submission using visible history.

        All eight fixed classical references are available equally to every agent.
        level_adjusted_weekly repeats the last week plus the recent day vs prior-week
        same-day mean difference. calendar_residual fits calendar effects plus historical
        residuals. Other methods use the named empirical distribution or weekly repeat.
        Plans use the same grid/ramp optimizer as TSFM plans. Conditional expected loss
        is not observed validation; comparing fitted expected losses does not identify
        the best future model. This track explicitly assigns zero credits to classical plans.
        """
        history = engine._series(series_id, 1)
        times = pd.date_range(contract["target_start"], periods=24, freq="h")
        samples, weights = classical_forecasts(history, times)[method]
        plan = optimize_marginals(samples * capacity_units(contract)[0], weights, contract)
        return dict(method=method, capacity_plan=plan, forecast_credits=0)

    return server


def main():
    make_server(Path(os.environ["FWB_EPISODE_DIR"]), os.environ["FWB_AS_OF"]).run()


if __name__ == "__main__":
    main()
