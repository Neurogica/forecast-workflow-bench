"""Load checksum-verified, agent-visible observations."""

from pathlib import Path

import pandas as pd

from forecast_workflow.core.io import digest
from forecast_workflow.core.schema import SeriesRecord


def load_frame(root: Path, record: SeriesRecord) -> pd.DataFrame:
    path = (root / record.path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("catalog path escapes data root")
    if digest(path) != record.sha256:
        raise ValueError(f"snapshot hash mismatch: {record.series_id}")
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError("timestamps must be unique and increasing")
    return frame
