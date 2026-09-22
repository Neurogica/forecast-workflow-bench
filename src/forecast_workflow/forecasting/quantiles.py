"""Opt-in marginal quantile tools, with separately named and metered forecast tariffs."""

from copy import copy
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import Field

from forecast_workflow.core.schema import Record
from forecast_workflow.forecasting.models import (
    chronos_bolt_pipeline,
    chronos_pipeline,
    timesfm_pipeline,
)

LEVELS = tuple(i / 10 for i in range(1, 10))


def validate_levels(levels):
    if not levels or len(levels) != len(set(levels)) or any(q not in LEVELS for q in levels):
        raise ValueError("quantiles must be unique native levels 0.1, 0.2, ..., 0.9")


def predict_quantiles(values, horizon, model, levels, season=168):
    validate_levels(levels)
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all() or not 1 <= horizon <= 336:
        raise ValueError("invalid finite history or horizon")
    if model == "seasonal_empirical":
        if season < 1 or len(values) < season:
            raise ValueError("empirical quantiles require a full weekly cycle")
        output = np.array(
            [
                np.quantile(
                    values[(len(values) + h) % season :: season], levels, method="inverted_cdf"
                )
                for h in range(horizon)
            ]
        )
    elif model == "chronos2":
        import torch

        result, _ = chronos_pipeline().predict_quantiles(
            inputs=[torch.tensor(values, dtype=torch.float32).reshape(1, -1)],
            prediction_length=horizon,
            quantile_levels=levels,
        )
        output = result[0].detach().cpu().numpy().reshape(horizon, len(levels))
    elif model == "chronos_bolt_tiny":
        import torch

        result, _ = chronos_bolt_pipeline().predict_quantiles(
            inputs=[torch.tensor(values, dtype=torch.float32)],
            prediction_length=horizon,
            quantile_levels=levels,
            limit_prediction_length=False,
        )
        output = result[0].detach().cpu().numpy().reshape(horizon, len(levels))
    elif model == "timesfm25":
        _, result = timesfm_pipeline().forecast(horizon=horizon, inputs=[values])
        output = np.asarray(result[0][:, [round(q * 10) for q in levels]], dtype=float)
    else:
        raise ValueError(
            "quantiles require seasonal_empirical, chronos2, timesfm25 or chronos_bolt_tiny"
        )
    if output.shape != (horizon, len(levels)) or not np.isfinite(output).all():
        raise ValueError("backend returned invalid quantiles")
    return output


class QuantileContract(Record):
    version: Literal["native-marginal-quantiles-v1"] = "native-marginal-quantiles-v1"
    models: list[str] = Field(min_length=1)


class QuantileTools:
    def __init__(self, engine, contract_path: Path):
        self.engine = engine
        self.contract = QuantileContract.model_validate_json(contract_path.read_text())
        if len(set(self.contract.models)) != len(self.contract.models) or any(
            m not in {"seasonal_empirical", "chronos2", "timesfm25", "chronos_bolt_tiny"}
            for m in self.contract.models
        ):
            raise ValueError("invalid probabilistic model pool")

    def capabilities(self):
        return dict(
            models=self.contract.models,
            quantile_levels=list(LEVELS),
            tariff_names={m: f"{m}_quantiles" for m in self.contract.models},
            model_notes={
                "chronos_bolt_tiny": {
                    "native_horizon_steps": 64,
                    "long_horizon": "Beyond 64 bins, the pinned library extends quantile paths "
                    "heuristically. Longer horizons have no calibration guarantee.",
                }
            }
            if "chronos_bolt_tiny" in self.contract.models
            else {},
            interpretation="Marginal quantiles for each timestamp; sums/maxima of these "
            "values are not quantiles of the corresponding aggregate random variable.",
        )

    def _prepare(self, series_id, model, horizon, context_steps, hours, levels):
        validate_levels(levels)
        if model not in self.contract.models:
            raise ValueError("model not enabled for quantile forecasts")
        series = self.engine._series(series_id, hours)
        if context_steps is not None:
            if not 2 <= context_steps <= len(series):
                raise ValueError("context unavailable")
            series = series.tail(context_steps)
        if model == "seasonal_empirical":
            self.engine._validate_prediction(series.values, horizon, "seasonal_naive", 168 // hours)
        else:
            self.engine._validate_prediction(series.values, horizon, model, 24 // hours)
        quote = (
            self.engine.meter.quote(f"{model}_quantiles", len(series), horizon)
            if self.engine.meter
            else {"enabled": False}
        )
        return series, quote

    def quote(self, series_id, model, horizon, context_steps=None, hours=1, levels=None):
        _, quote = self._prepare(
            series_id,
            model,
            horizon,
            context_steps,
            hours,
            [0.5, 0.8] if levels is None else levels,
        )
        if self.engine.meter:
            quote["affordable"] = quote["credits"] <= self.engine.meter.status()["remaining"]
        return quote

    def forecast(self, series_id, model, horizon, context_steps=None, hours=1, levels=None):
        levels = [0.5, 0.8] if levels is None else levels
        series, quote = self._prepare(series_id, model, horizon, context_steps, hours, levels)
        meter = self.engine.meter
        if meter:
            meter.charge(quote)
        try:
            result = predict_quantiles(series.values, horizon, model, levels, 168 // hours)
        except BaseException:
            if meter:
                meter.finish("backend_error")
            raise
        if meter:
            meter.finish("completed")
        times = pd.date_range(
            series.index[-1] + pd.Timedelta(hours=hours),
            periods=horizon,
            freq=f"{hours}h",
        )
        return dict(
            series_id=series_id,
            model=model,
            timestamp=[t.isoformat() for t in times],
            quantiles={str(q): result[:, i].tolist() for i, q in enumerate(levels)},
            unit=self.engine.records[series_id].unit,
            context_steps=len(series),
            hours=hours,
            interpretation=self.capabilities()["interpretation"],
            **({"forecast_budget": meter.status()} if meter else {}),
        )

    def replay(self, series_id, model, origin, horizon, context_steps, hours=1, levels=None):
        cutoff = pd.Timestamp(origin)
        if cutoff.tzinfo is None or cutoff > self.engine.as_of:
            raise ValueError("replay origin requires a timezone and must not exceed as_of")
        replay = copy(self)
        replay.engine = copy(self.engine)
        replay.engine.as_of = cutoff
        replay.engine.frames = {
            sid: frame[frame.timestamp <= cutoff].copy()
            for sid, frame in self.engine.frames.items()
        }
        result = replay.forecast(series_id, model, horizon, context_steps, hours, levels)
        result["origin"] = cutoff.isoformat()
        return result
