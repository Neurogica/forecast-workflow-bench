from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from forecast_workflow.core.io import digest, write_json
from forecast_workflow.core.schema import Catalog, SeriesRecord


@pytest.fixture
def catalog_dir(tmp_path):
    # Synthetic observations are only test fixtures, never benchmark samples.
    times = pd.date_range("2026-01-01", periods=24 * 30, freq="h", tz="UTC")
    path = tmp_path / "series.csv"
    pd.DataFrame({"timestamp": times, "value": np.arange(len(times), dtype=float)}).to_csv(
        path, index=False
    )
    record = SeriesRecord(
        series_id="fixture",
        name="TEST FIXTURE",
        path="series.csv",
        unit="u",
        source="unit test",
        source_url="https://example.invalid",
        license_id="CC0-1.0",
        attribution="test",
        sha256=digest(path),
        observed_start=times[0].to_pydatetime(),
        observed_end=times[-1].to_pydatetime(),
        snapshot_at=datetime.now(timezone.utc),
        quality="synthetic test fixture",
    )
    write_json(tmp_path / "catalog.json", Catalog(series=[record]).model_dump(mode="json"))
    return tmp_path
