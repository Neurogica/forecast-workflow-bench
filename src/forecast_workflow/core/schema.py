"""Versioned public contracts. Gold answers never enter the tool server."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SeriesRecord(Record):
    series_id: str
    name: str
    path: str
    unit: str
    frequency: Literal["1h"] = "1h"
    source: str
    source_url: str
    license_id: str
    attribution: str
    sha256: str
    observed_start: datetime
    observed_end: datetime
    snapshot_at: datetime
    quality: str


class Catalog(Record):
    schema_version: Literal["0.1"] = "0.1"
    series: list[SeriesRecord]

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [s.series_id for s in self.series]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate series_id")
        return self


class Task(Record):
    schema_version: Literal["0.1"] = "0.1"
    task_id: str
    group_id: str
    split: Literal["dev", "test"]
    family: str
    instruction: str
    as_of: AwareDatetime
    catalog: str = "catalog.json"
    max_calls: int = Field(default=24, ge=1, le=100)
    allowed_tools: list[str] | None = None
    max_output_tokens: int = Field(default=4096, ge=1024, le=32768)


class Answer(Record):
    series_id: str
    model: str
    start: AwareDatetime
    end: AwareDatetime
    statistic: Literal["mean", "sum", "max", "last"]
    quantile: float | None = Field(default=None, gt=0, lt=1)
    unit: str
    value: float
    context_steps: int | None = Field(default=None, ge=2)
    horizon: int | None = Field(default=None, ge=1, le=336)
    hours: Literal[1, 3, 6, 24] | None = None


class Decision(Record):
    decision_id: str
    value: float
    forecast_id: str | None = None


class Submission(Record):
    answers: list[Answer] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    status: Literal["ok", "blocked"] = "ok"
    reason_code: (
        Literal[
            "insufficient_history",
            "unsupported_horizon",
            "unsupported_quantile",
            "unavailable_model",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def valid_outcome(self):
        if self.status == "ok" and (
            not (self.answers or self.decisions) or self.reason_code is not None
        ):
            raise ValueError("ok requires answers and no reason_code")
        if self.status == "blocked" and (
            self.answers or self.decisions or self.reason_code is None
        ):
            raise ValueError("blocked requires a reason_code and no answers")
        return self
