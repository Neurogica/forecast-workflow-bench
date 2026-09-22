"""MCP stdio server. Run against an episode's public directory only."""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from forecast_workflow.forecasting.engine import ForecastTools
from forecast_workflow.tools.calculator import calculate as arithmetic


def make_server(root: Path, as_of: str) -> FastMCP:
    log = os.environ.get("FWB_BUDGET_LOG")
    engine = ForecastTools(root, as_of, Path(log) if log else None)
    server = FastMCP("forecast-workflow-bench")
    quantile_tools = None
    if (root / "probabilistic_forecasts.json").exists():
        from forecast_workflow.forecasting.quantiles import QuantileTools

        quantile_tools = QuantileTools(engine, root / "probabilistic_forecasts.json")

        @server.tool()
        def quote_quantile_forecast(
            series_id: str,
            model: str,
            horizon: int,
            context_steps: int | None = None,
            hours: int = 1,
            levels: list[float] | None = None,
        ) -> dict:
            """Quote one native marginal-quantile call; separately priced *_quantiles tariff."""
            return quantile_tools.quote(series_id, model, horizon, context_steps, hours, levels)

        @server.tool()
        def forecast_quantiles(
            series_id: str,
            model: str,
            horizon: int,
            context_steps: int | None = None,
            hours: int = 1,
            levels: list[float] | None = None,
        ) -> dict:
            """Marginal q0.1..q0.9 at each future timestamp; default q0.5/q0.8. One charged call.

            Not a distribution of sums or maxima. hours=1/3/6/24 uses complete-bin means.
            """
            return quantile_tools.forecast(series_id, model, horizon, context_steps, hours, levels)

        @server.tool()
        def replay_quantiles(
            series_id: str,
            model: str,
            origin: str,
            horizon: int,
            context_steps: int,
            hours: int = 1,
            levels: list[float] | None = None,
        ) -> dict:
            """Paid past-only quantile forecast for validation; origin must not exceed as_of."""
            return quantile_tools.replay(
                series_id, model, origin, horizon, context_steps, hours, levels
            )

    if engine.meter is not None:

        @server.tool()
        def budget_status() -> dict:
            """Published forecast tariffs, spent/remaining credits. No charge for inspection."""
            return engine.budget_status()

        @server.tool()
        def quote_forecast(
            series_id: str,
            model: str,
            horizon: int,
            context_steps: int | None = None,
            hours: int = 1,
        ) -> dict:
            """Quote one forecast without execution. Backtest pays every model/fold separately."""
            return engine.quote_forecast(series_id, model, horizon, context_steps, hours)

    @server.tool()
    def calculate(expression: str) -> dict:
        """Arithmetic: + - * /, lists, sum/min/max/sorted/abs/len, slices e.g. [-3:]. No I/O."""
        return arithmetic(expression)

    @server.tool()
    def catalog() -> dict:
        """Discover available series, units, model names, and the observation cutoff."""
        result = engine.catalog()
        if quantile_tools is not None:
            result["probabilistic_forecasts"] = quantile_tools.capabilities()
        return result

    @server.tool()
    def inspect_series(series_id: str, hours: int = 1) -> dict:
        """Inspect count, missingness and coverage. hours=1,3,6,24; UTC complete-bin means."""
        return engine.inspect_series(series_id, hours)

    @server.tool()
    def history(series_id: str, limit: int = 48, hours: int = 1) -> dict:
        """Read up to 336 visible observations; missing values are null. No future data."""
        return engine.history(series_id, limit, hours)

    @server.tool()
    def backtest(
        series_id: str,
        models: list[str],
        horizon: int = 24,
        folds: int = 3,
        metric: str = "mae",
        hours: int = 1,
        context_steps: int | None = None,
    ) -> dict:
        """Past-only MAE/RMSE. context_steps sets training bins per fold; null=expanding."""
        return engine.backtest(series_id, models, horizon, folds, metric, hours, context_steps)

    @server.tool()
    def forecast(
        series_id: str,
        model: str,
        horizon: int,
        hours: int = 1,
        context_steps: int | None = None,
    ) -> dict:
        """Forecast 1..336 bins. hours=1/3/6/24 means; context_steps=history bins, null=all."""
        return engine.forecast(series_id, model, horizon, hours, context_steps)

    @server.tool()
    def replay_forecast(
        series_id: str,
        model: str,
        origin: str,
        horizon: int,
        context_steps: int,
        hours: int = 1,
    ) -> dict:
        """Forecast from a past cutoff, training only on data at/before origin. Returns artifact."""
        return engine.replay_forecast(series_id, model, origin, horizon, context_steps, hours)

    @server.tool()
    def summarize(forecast_id: str, start: str, end: str, statistic: str) -> dict:
        """Reduce inclusive endpoints. statistic=mean/sum/max/last. UTC offsets required."""
        return engine.summarize(forecast_id, start, end, statistic)

    return server


def main():
    root = Path(os.environ["FWB_EPISODE_DIR"])
    make_server(root, os.environ["FWB_AS_OF"]).run(transport="stdio")


if __name__ == "__main__":
    main()
