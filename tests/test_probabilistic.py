import numpy as np
import pytest

from forecast_workflow.core.io import write_json
from forecast_workflow.forecasting.engine import ForecastTools
from forecast_workflow.forecasting.quantiles import QuantileTools, predict_quantiles


def tools(root, budget=15):
    write_json(root / "probabilistic_forecasts.json", {"models": ["seasonal_empirical"]})
    write_json(
        root / "forecast_budget.json",
        {
            "profile_id": "unit-test",
            "unit": "test credits",
            "budget": budget,
            "evidence_sha256": "fixture",
            "rates": [
                {
                    "model": "seasonal_empirical_quantiles",
                    "context_limit": 336,
                    "horizon_limit": 24,
                    "credits": 10,
                }
            ],
        },
    )
    engine = ForecastTools(root, "2026-01-25T00:00Z")
    return QuantileTools(engine, root / "probabilistic_forecasts.json")


def test_weekly_empirical_distribution_matches_two_prior_weeks():
    history = np.r_[np.arange(168), np.arange(168) + 100]
    output = predict_quantiles(history, 3, "seasonal_empirical", [0.5, 0.8])
    np.testing.assert_allclose(output, [[0, 100], [1, 101], [2, 102]])


def test_quantile_meter_rejects_second_forecast_before_backend(catalog_dir):
    q = tools(catalog_dir)
    before = q.engine.meter.status()["spent"]
    assert q.quote("fixture", "seasonal_empirical", 24, 336)["credits"] == 10
    assert q.engine.meter.status()["spent"] == before
    output = q.forecast("fixture", "seasonal_empirical", 24, 336)
    assert list(output["quantiles"]) == ["0.5", "0.8"]
    assert output["forecast_budget"]["spent"] == 10
    assert "not quantiles" in output["interpretation"]
    with pytest.raises(ValueError, match="budget exceeded"):
        q.forecast("fixture", "seasonal_empirical", 24, 336)
    assert q.engine.meter.status()["spent"] == 10


def test_invalid_levels_and_short_week_are_free(catalog_dir):
    q = tools(catalog_dir)
    for levels in [[], [0.5, 0.5], [0.95]]:
        with pytest.raises(ValueError, match="quantiles"):
            q.forecast("fixture", "seasonal_empirical", 24, 336, levels=levels)
    with pytest.raises(ValueError, match="insufficient history"):
        q.forecast("fixture", "seasonal_empirical", 24, 96)
    assert q.engine.meter.status()["spent"] == 0


def test_quantile_backend_failure_keeps_its_charge(catalog_dir, monkeypatch):
    q = tools(catalog_dir)

    def fail(*args):
        raise RuntimeError("backend down")

    monkeypatch.setattr("forecast_workflow.forecasting.quantiles.predict_quantiles", fail)
    with pytest.raises(RuntimeError, match="backend down"):
        q.forecast("fixture", "seasonal_empirical", 24, 336)
    assert q.engine.meter.status()["spent"] == 10
    assert q.engine.meter.entries[-1]["status"] == "backend_error"


def test_replay_crops_future_and_shares_meter(catalog_dir):
    q = tools(catalog_dir)
    original_end = q.engine._series("fixture").index[-1]
    output = q.replay("fixture", "seasonal_empirical", "2026-01-24T00:00Z", 24, 336)
    assert output["timestamp"][0] == "2026-01-24T01:00:00+00:00"
    assert q.engine._series("fixture").index[-1] == original_end
    assert q.engine.meter.status()["spent"] == 10
    with pytest.raises(ValueError, match="must not exceed"):
        q.replay("fixture", "seasonal_empirical", "2026-01-26T00:00Z", 24, 336)
