"""Stateful forecasting tools. Only visible observations may enter this engine."""

from copy import copy
from pathlib import Path

import numpy as np
import pandas as pd

from forecast_workflow.budget.meter import CostMeter, ForecastBudget
from forecast_workflow.core.schema import Answer, Catalog
from forecast_workflow.data.loading import load_frame
from forecast_workflow.forecasting.models import available_models, predict, rolling_scores


class ForecastTools:
    def __init__(self, root: Path, as_of: str, budget_log: Path | None = None):
        self.root = root
        self.as_of = pd.Timestamp(as_of)
        if self.as_of.tzinfo is None:
            raise ValueError("as_of requires an explicit timezone")
        catalog = Catalog.model_validate_json((root / "catalog.json").read_text())
        self.records = {s.series_id: s for s in catalog.series}
        self.frames = {}
        for key, record in self.records.items():
            frame = load_frame(root, record)
            # Defense in depth; build also physically removes future rows.
            self.frames[key] = frame[frame.timestamp <= self.as_of].copy()
        self.artifacts: dict[str, tuple[str, str, pd.Series]] = {}
        budget_path = root / "forecast_budget.json"
        self.meter = (
            CostMeter(ForecastBudget.model_validate_json(budget_path.read_text()), budget_log)
            if budget_path.exists()
            else None
        )

    def _validate_prediction(self, values, horizon, model, season):
        if model not in available_models():
            raise ValueError("model unavailable")
        if len(values) < 2 or not np.isfinite(values).all() or not 1 <= horizon <= 336:
            raise ValueError("invalid prediction input or horizon")
        if model == "seasonal_naive" and len(values) < season:
            raise ValueError("insufficient history for one seasonal cycle")

    def _predict(self, values, horizon, model, season):
        self._validate_prediction(values, horizon, model, season)
        if self.meter is None:
            return predict(values, horizon, model, season)
        quote = self.meter.quote(model, len(values), horizon)
        self.meter.charge(quote)
        try:
            result = predict(values, horizon, model, season)
        except BaseException:
            self.meter.finish("backend_error")
            raise
        self.meter.finish("completed")
        return result

    def budget_status(self) -> dict:
        if self.meter is None:
            return {"enabled": False}
        return dict(
            **self.meter.status(), rates=[r.model_dump() for r in self.meter.contract.rates]
        )

    def quote_forecast(self, series_id, model, horizon, context_steps=None, hours=1) -> dict:
        series = self._series(series_id, hours)
        if context_steps is not None:
            if not 2 <= context_steps <= len(series):
                raise ValueError("context unavailable")
            series = series.tail(context_steps)
        self._validate_prediction(series.values, horizon, model, 24 // hours)
        if self.meter is None:
            return {"enabled": False}
        quote = self.meter.quote(model, len(series), horizon)
        return dict(**quote, affordable=quote["credits"] <= self.meter.status()["remaining"])

    def catalog(self) -> dict:
        return {
            "series": [
                {"series_id": r.series_id, "name": r.name, "unit": r.unit, "frequency": r.frequency}
                for r in self.records.values()
            ],
            "models": [
                m
                for m in available_models()
                if self.meter is None or m in {r.model for r in self.meter.contract.rates}
            ],
            "as_of": self.as_of.isoformat(),
            **({"forecast_budget": self.budget_status()} if self.meter else {}),
        }

    def _series(self, series_id: str, hours: int = 1) -> pd.Series:
        if hours not in {1, 3, 6, 24}:
            raise ValueError("hours must be 1, 3, 6, or 24")
        frame = self.frames[series_id]
        if frame.empty:
            raise ValueError("no visible observations")
        series = frame.set_index("timestamp").value.asfreq("h")
        if hours != 1:
            first_observation = series.index[0]
            last_observation = series.index[-1]
            # Mean of hourly point samples; keep only complete UTC-aligned bins.
            resampler = series.resample(f"{hours}h", origin="epoch", label="left", closed="left")
            counts = resampler.count()
            series = resampler.mean().where(counts == hours)
            series = series[
                (series.index >= first_observation)
                & (series.index + pd.Timedelta(hours=hours - 1) <= last_observation)
            ]
        if series.empty:
            raise ValueError("no complete time bins")
        return series

    def inspect_series(self, series_id: str, hours: int = 1) -> dict:
        series = self._series(series_id, hours)
        return {
            "series_id": series_id,
            "count": len(series),
            "missing_fraction": float(series.isna().mean()),
            "start": series.index[0].isoformat(),
            "end": series.index[-1].isoformat(),
            "unit": self.records[series_id].unit,
            "hours": hours,
        }

    def history(self, series_id: str, limit: int = 48, hours: int = 1) -> dict:
        if not 1 <= limit <= 336:
            raise ValueError("limit must be 1..336")
        series = self._series(series_id, hours).tail(limit)
        return {
            "series_id": series_id,
            "timestamp": [t.isoformat() for t in series.index],
            "value": [None if pd.isna(v) else float(v) for v in series.values],
        }

    def backtest(
        self,
        series_id: str,
        models: list[str],
        horizon: int = 24,
        folds: int = 3,
        metric: str = "mae",
        hours: int = 1,
        context_steps: int | None = None,
    ) -> dict:
        if not models or len(set(models)) != len(models):
            raise ValueError("models must be nonempty and unique")
        if any(m not in available_models() for m in models):
            raise ValueError("model unavailable")
        series = self._series(series_id, hours)
        if self.meter is not None:
            if not 1 <= folds <= 5 or not 1 <= horizon <= 336 or metric not in {"mae", "rmse"}:
                raise ValueError("invalid backtest contract")
            if len(series) - folds * horizon < max(24 // hours, 2):
                raise ValueError("insufficient history for rolling validation")
            quotes = []
            for model in models:
                for fold in range(folds, 0, -1):
                    cut = len(series) - fold * horizon
                    if context_steps is not None and not 2 <= context_steps <= cut:
                        raise ValueError("context unavailable in validation fold")
                    train = (
                        series.iloc[:cut]
                        if context_steps is None
                        else series.iloc[cut - context_steps : cut]
                    )
                    self._validate_prediction(train.values, horizon, model, 24 // hours)
                    if not np.isfinite(series.iloc[cut : cut + horizon]).all():
                        raise ValueError("missing validation observations")
                    quotes.append(self.meter.quote(model, len(train), horizon))
            self.meter.preflight(quotes)
        scores = rolling_scores(
            series.values,
            horizon,
            folds,
            24 // hours,
            models,
            metric,
            context_steps,
            predictor=self._predict if self.meter else None,
        )
        best = min(scores, key=lambda m: (scores[m], m))
        return {
            "series_id": series_id,
            "metric": metric,
            "scores": scores,
            "best_model": best,
            "tie_break": "lexicographic model name",
            **({"forecast_budget": self.meter.status()} if self.meter else {}),
        }

    def forecast(
        self,
        series_id: str,
        model: str,
        horizon: int,
        hours: int = 1,
        context_steps: int | None = None,
    ) -> dict:
        series = self._series(series_id, hours)
        if context_steps is not None:
            if not 2 <= context_steps <= len(series):
                raise ValueError("context_steps must be 2..available bin count")
            series = series.tail(context_steps)
        values = self._predict(series.values, horizon, model, 24 // hours)
        times = pd.date_range(
            series.index[-1] + pd.Timedelta(hours=hours), periods=horizon, freq=f"{hours}h"
        )
        key = f"forecast_{len(self.artifacts)}"
        self.artifacts[key] = (series_id, model, pd.Series(values, index=times))
        return {
            "forecast_id": key,
            "series_id": series_id,
            "model": model,
            "timestamp": [t.isoformat() for t in times],
            "value": values.tolist(),
            "unit": self.records[series_id].unit,
            "hours": hours,
            "context_steps": len(series),
            **({"forecast_budget": self.meter.status()} if self.meter else {}),
        }

    def replay_forecast(
        self,
        series_id: str,
        model: str,
        origin: str,
        horizon: int,
        context_steps: int,
        hours: int = 1,
    ) -> dict:
        cutoff = pd.Timestamp(origin)
        if cutoff.tzinfo is None or cutoff > self.as_of:
            raise ValueError("replay origin must be timezone-aware and no later than as_of")
        replay = copy(self)
        replay.as_of = cutoff
        replay.frames = {key: f[f.timestamp <= cutoff].copy() for key, f in self.frames.items()}
        result = replay.forecast(series_id, model, horizon, hours, context_steps)
        result["origin"] = cutoff.isoformat()
        return result

    def summarize(self, forecast_id: str, start: str, end: str, statistic: str) -> dict:
        """Reduce predictions in an inclusive timestamp interval; never extrapolate silently."""
        series_id, model, series = self.artifacts[forecast_id]
        begin, finish = pd.Timestamp(start), pd.Timestamp(end)
        if begin.tzinfo is None or finish.tzinfo is None:
            raise ValueError("timestamps require explicit timezone")
        if begin > finish or begin not in series.index or finish not in series.index:
            raise ValueError("requested endpoints must exist in forecast; extend horizon if needed")
        selected = series.loc[begin:finish]
        if statistic not in {"mean", "sum", "max", "last"}:
            raise ValueError("statistic must be mean, sum, max, or last")
        value = float(selected.iloc[-1] if statistic == "last" else getattr(selected, statistic)())
        if not np.isfinite(value):
            raise ValueError("non-finite result")
        return Answer(
            series_id=series_id,
            model=model,
            start=begin.to_pydatetime(),
            end=finish.to_pydatetime(),
            statistic=statistic,
            unit=self.records[series_id].unit,
            value=value,
        ).model_dump(mode="json")
