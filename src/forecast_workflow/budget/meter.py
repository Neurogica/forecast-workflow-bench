"""Published reference tariffs and a durable, per-episode forecast ledger."""

from pathlib import Path

from pydantic import Field, model_validator

from forecast_workflow.core.io import write_json
from forecast_workflow.core.schema import Record


class Rate(Record):
    model: str
    context_limit: int = Field(ge=2)
    horizon_limit: int = Field(ge=1, le=336)
    credits: int = Field(gt=0)


class ForecastBudget(Record):
    profile_id: str
    unit: str
    budget: int = Field(ge=0)
    rates: list[Rate] = Field(min_length=1)
    evidence_sha256: str

    @model_validator(mode="after")
    def unique_rates(self):
        keys = [(r.model, r.context_limit, r.horizon_limit) for r in self.rates]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate cost cells")
        return self


class CostMeter:
    def __init__(self, contract: ForecastBudget, log_path: Path | None = None):
        self.contract = contract
        self.log_path = log_path
        self.entries: list[dict] = []
        self.spent = 0
        self.persist()

    def quote(self, model: str, context: int, horizon: int) -> dict:
        eligible = [
            r
            for r in self.contract.rates
            if r.model == model and context <= r.context_limit and horizon <= r.horizon_limit
        ]
        if context < 2 or horizon < 1 or not eligible:
            raise ValueError("model or shape outside published cost profile")
        rate = min(eligible, key=lambda r: (r.context_limit, r.horizon_limit))
        return dict(
            model=model,
            context_steps=context,
            horizon=horizon,
            credits=rate.credits,
            context_bucket=rate.context_limit,
            horizon_bucket=rate.horizon_limit,
        )

    def preflight(self, quotes: list[dict]):
        if sum(q["credits"] for q in quotes) > self.contract.budget - self.spent:
            raise ValueError("forecast budget exceeded; no prediction started")

    def charge(self, quote: dict):
        self.preflight([quote])
        self.spent += quote["credits"]
        self.entries.append(dict(**quote, status="started"))
        # Persist before inference so timeouts and backend errors retain their charge.
        self.persist()

    def finish(self, status: str):
        self.entries[-1]["status"] = status
        self.persist()

    def status(self) -> dict:
        return dict(
            profile_id=self.contract.profile_id,
            unit=self.contract.unit,
            budget=self.contract.budget,
            spent=self.spent,
            remaining=self.contract.budget - self.spent,
            predictions=len(self.entries),
        )

    def persist(self):
        if self.log_path is not None:
            write_json(self.log_path, dict(**self.status(), entries=self.entries))
