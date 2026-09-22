import json

import pytest

from forecast_workflow.core.io import write_json
from forecast_workflow.forecasting.engine import ForecastTools


def engine(root, budget=20):
    write_json(
        root / "forecast_budget.json",
        dict(
            profile_id="test",
            unit="fixture credits",
            budget=budget,
            evidence_sha256="test",
            rates=[
                dict(model=m, context_limit=1000, horizon_limit=336, credits=c)
                for m, c in [("naive", 3), ("seasonal_naive", 5)]
            ],
        ),
    )
    return ForecastTools(root, "2026-01-30T23:00:00Z", root / "ledger.json")


def test_atomic_backtest_and_shared_replay_budget(catalog_dir, monkeypatch):
    e = engine(catalog_dir, 15)
    import forecast_workflow.forecasting.engine as module

    original = module.predict
    calls = []

    def record(*args):
        calls.append(args[2])
        return original(*args)

    monkeypatch.setattr(module, "predict", record)
    with pytest.raises(ValueError, match="budget exceeded"):
        e.backtest("fixture", ["naive", "seasonal_naive"], 24, 2)
    assert calls == [] and e.meter.spent == 0
    e.backtest("fixture", ["naive", "seasonal_naive"], 24, 1)
    assert calls == ["naive", "seasonal_naive"] and e.meter.spent == 8
    e.replay_forecast("fixture", "naive", "2026-01-20T23:00:00Z", 24, 96)
    assert e.meter.spent == 11
    e.forecast("fixture", "naive", 24, context_steps=96)
    assert e.meter.spent == 14
    with pytest.raises(ValueError, match="budget exceeded"):
        e.forecast("fixture", "naive", 24, context_steps=96)
    assert len(calls) == 4


def test_failed_backend_retains_charge_invalid_input_is_free(catalog_dir, monkeypatch):
    e = engine(catalog_dir)
    with pytest.raises(ValueError):
        e.forecast("fixture", "naive", 1000)
    assert e.meter.spent == 0

    def fail(*args):
        # Charge is durable BEFORE the backend starts.
        assert json.loads((catalog_dir / "ledger.json").read_text())["spent"] == 3
        raise RuntimeError("backend failed")

    monkeypatch.setattr("forecast_workflow.forecasting.engine.predict", fail)
    with pytest.raises(RuntimeError):
        e.forecast("fixture", "naive", 24)
    assert e.meter.spent == 3
    assert e.meter.entries[-1]["status"] == "backend_error"


def test_quotes_and_artifacts_are_free_recomputation_is_not(catalog_dir):
    e = engine(catalog_dir, 6)
    assert e.quote_forecast("fixture", "naive", 24)["credits"] == 3
    assert e.meter.spent == 0
    f = e.forecast("fixture", "naive", 24)
    e.summarize(f["forecast_id"], f["timestamp"][0], f["timestamp"][-1], "sum")
    assert e.meter.spent == 3
    e.forecast("fixture", "naive", 24)
    assert e.meter.spent == 6


async def test_budget_real_mcp(catalog_dir):
    import sys
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    engine(catalog_dir, 3)
    log = catalog_dir / "mcp-ledger.json"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "forecast_workflow.tools.forecast"],
        env={
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
            "FWB_EPISODE_DIR": str(catalog_dir),
            "FWB_AS_OF": "2026-01-30T23:00:00Z",
            "FWB_BUDGET_LOG": str(log),
        },
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert {"budget_status", "quote_forecast"} <= names
            args = dict(series_id="fixture", model="naive", horizon=24, context_steps=96)
            assert not (await session.call_tool("forecast", args)).isError
            assert (await session.call_tool("forecast", args)).isError
    assert json.loads(log.read_text())["spent"] == 3
