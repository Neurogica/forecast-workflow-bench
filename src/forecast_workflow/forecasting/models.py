"""Small deterministic baselines plus an optional revision-pinned Chronos adapter."""

import os
from functools import lru_cache

import numpy as np

STATISTICAL_MODELS = ("naive", "seasonal_naive", "drift")


def available_models() -> list[str]:
    models = list(STATISTICAL_MODELS)
    if os.environ.get("FWB_CHRONOS_REVISION"):
        models.append("chronos2")
    if os.environ.get("FWB_TIMESFM_REVISION"):
        models.append("timesfm25")
    if os.environ.get("FWB_BOLT_REVISION"):
        models.append("chronos_bolt_tiny")
    return models


@lru_cache(maxsize=1)
def timesfm_pipeline():
    import timesfm

    revision = os.environ.get("FWB_TIMESFM_REVISION", "")
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("FWB_TIMESFM_REVISION must be a full immutable commit SHA")
    pipeline = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
        "google/timesfm-2.5-200m-pytorch",
        revision=revision,
        torch_compile=False,
    )
    pipeline.compile(
        timesfm.ForecastConfig(
            max_context=1024,
            max_horizon=512,
            normalize_inputs=True,
            use_continuous_quantile_head=True,
            force_flip_invariance=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
        )
    )
    return pipeline


@lru_cache(maxsize=1)
def chronos_bolt_pipeline():
    from chronos import ChronosBoltPipeline

    revision = os.environ.get("FWB_BOLT_REVISION", "")
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("FWB_BOLT_REVISION must be a full immutable commit SHA")
    return ChronosBoltPipeline.from_pretrained(
        "amazon/chronos-bolt-tiny",
        revision=revision,
        device_map=os.environ.get("FWB_MODEL_DEVICE", "cpu"),
    )


@lru_cache(maxsize=1)
def chronos_pipeline():
    from chronos import Chronos2Pipeline

    revision = os.environ.get("FWB_CHRONOS_REVISION", "")
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("FWB_CHRONOS_REVISION must be a full immutable commit SHA")
    return Chronos2Pipeline.from_pretrained(
        "amazon/chronos-2",
        revision=revision,
        device_map=os.environ.get("FWB_MODEL_DEVICE", "cpu"),
    )


def predict(values: np.ndarray, horizon: int, model: str, season: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("at least two finite observations required; inspect missingness first")
    if horizon < 1 or horizon > 336:
        raise ValueError("horizon must be between 1 and 336")
    if model == "naive":
        return np.repeat(values[-1], horizon)
    if model == "seasonal_naive":
        if len(values) < season:
            raise ValueError("insufficient history for one seasonal cycle")
        return np.resize(values[-season:], horizon)
    if model == "drift":
        return values[-1] + np.arange(1, horizon + 1) * (values[-1] - values[0]) / (len(values) - 1)
    if model == "timesfm25":
        _, quantiles = timesfm_pipeline().forecast(horizon=horizon, inputs=[values])
        # TimesFM channels: mean, q0.1,...,q0.9; use q0.5 for both TSFMs.
        return np.asarray(quantiles[0, :, 5], dtype=float)
    if model == "chronos_bolt_tiny":
        import torch

        quantiles, _ = chronos_bolt_pipeline().predict_quantiles(
            inputs=[torch.tensor(values, dtype=torch.float32)],
            prediction_length=horizon,
            quantile_levels=[0.5],
            limit_prediction_length=False,
        )
        return quantiles[0][..., 0].detach().cpu().numpy().reshape(-1)
    if model == "chronos2":
        import torch

        quantiles, _ = chronos_pipeline().predict_quantiles(
            inputs=[torch.tensor(values, dtype=torch.float32).reshape(1, -1)],
            prediction_length=horizon,
            quantile_levels=[0.5],
        )
        # Chronos calls its second output "mean", but it is the median.
        # Select q=0.5 explicitly; window means aggregate these point forecasts.
        return quantiles[0][..., 0].detach().cpu().numpy().reshape(-1)
    raise ValueError(f"unsupported model: {model}")


def rolling_scores(
    values: np.ndarray,
    horizon: int,
    folds: int,
    season: int,
    models: list[str],
    metric: str,
    context_steps: int | None = None,
    predictor=None,
) -> dict[str, float]:
    if context_steps is not None and context_steps < 2:
        raise ValueError("context_steps must be at least 2")
    if not 1 <= horizon <= 336:
        raise ValueError("horizon must be between 1 and 336")
    if metric not in {"mae", "rmse"} or not 1 <= folds <= 5:
        raise ValueError("metric must be mae/rmse; folds must be 1..5")
    if len(values) - folds * horizon < max(season, 2):
        raise ValueError("insufficient history for requested rolling validation")
    scores = {}
    for model in models:
        errors = []
        for fold in range(folds, 0, -1):
            cut = len(values) - fold * horizon
            if context_steps is not None and context_steps > cut:
                raise ValueError("requested context unavailable in earliest validation fold")
            train = values[:cut] if context_steps is None else values[cut - context_steps : cut]
            error = (predictor or predict)(train, horizon, model, season) - values[
                cut : cut + horizon
            ]
            errors.append(
                float(np.abs(error).mean() if metric == "mae" else np.sqrt(np.square(error).mean()))
            )
        scores[model] = float(np.mean(errors))
    return scores
