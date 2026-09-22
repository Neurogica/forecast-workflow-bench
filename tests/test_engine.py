import json

import numpy as np
import pandas as pd
import pytest

from forecast_workflow.core.io import digest
from forecast_workflow.forecasting.engine import ForecastTools
from forecast_workflow.forecasting.models import predict, rolling_scores


def test_future_observations_never_enter_tools(catalog_dir):
    engine = ForecastTools(catalog_dir, "2026-01-10T23:00:00Z")
    history = engine.history("fixture", limit=336)
    assert len(history["value"]) == 240
    assert history["value"][-1] == 239
    forecast = engine.forecast("fixture", "naive", 2)
    assert forecast["value"] == [239, 239]
    assert pd.Timestamp(forecast["timestamp"][0]) == pd.Timestamp("2026-01-11T00:00:00Z")


def test_complete_bins_and_no_partial_resampling(catalog_dir):
    engine = ForecastTools(catalog_dir, "2026-01-10T01:00:00Z")
    history = engine.history("fixture", hours=3)
    assert pd.Timestamp(history["timestamp"][-1]) == pd.Timestamp("2026-01-09T21:00:00Z")
    assert history["value"][-1] == np.mean([213, 214, 215])


def test_horizon_must_cover_requested_window(catalog_dir):
    engine = ForecastTools(catalog_dir, "2026-01-10T23:00:00Z")
    f = engine.forecast("fixture", "drift", 24)
    answer = engine.summarize(
        f["forecast_id"], "2026-01-11T06:00:00Z", "2026-01-11T08:00:00Z", "mean"
    )
    assert answer["value"] == 247
    with pytest.raises(ValueError, match="endpoints"):
        engine.summarize(f["forecast_id"], "2026-01-11T06:00:00Z", "2026-01-12T08:00:00Z", "mean")


def test_rolling_validation_finds_drift_without_future():
    scores = rolling_scores(np.arange(200.0), 24, 3, 24, ["drift", "naive"], "mae")
    assert scores["drift"] == 0
    assert scores["naive"] == 12.5


def test_missing_values_do_not_silently_change_cadence():
    with pytest.raises(ValueError, match="finite"):
        predict(np.array([1, np.nan, 3]), 2, "naive", 1)


def test_hash_mismatch_rejected(catalog_dir):
    with (catalog_dir / "series.csv").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="hash"):
        ForecastTools(catalog_dir, "2026-01-10T00:00:00Z")


@pytest.mark.parametrize(
    "hours,end",
    [(3, "2026-01-30T18:00:00Z"), (6, "2026-01-30T12:00:00Z"), (24, "2026-01-29T00:00:00Z")],
)
def test_delayed_source_drops_incomplete_trailing_bins(catalog_dir, hours, end):
    path = catalog_dir / "series.csv"
    frame = pd.read_csv(path).iloc[:-2]
    frame.to_csv(path, index=False)
    catalog_path = catalog_dir / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["series"][0].update(sha256=digest(path), observed_end=frame.timestamp.iloc[-1])
    catalog_path.write_text(json.dumps(catalog))
    engine = ForecastTools(catalog_dir, "2026-01-31T00:00:00Z")
    history = engine.history("fixture", hours=hours)
    assert pd.Timestamp(history["timestamp"][-1]) == pd.Timestamp(end)
    assert all(v is not None for v in history["value"])
    forecast = engine.forecast("fixture", "naive", 2, hours=hours)
    assert forecast["value"] == [history["value"][-1]] * 2


def test_aggregation_keeps_internal_missing_bin(catalog_dir):
    engine = ForecastTools(catalog_dir, "2026-01-30T23:00:00Z")
    engine.frames["fixture"].loc[100, "value"] = np.nan
    series = engine._series("fixture", hours=3)
    assert len(series) == 240
    assert int(series.isna().sum()) == 1
