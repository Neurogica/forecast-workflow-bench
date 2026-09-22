"""Eight fixed classical predictive distributions; no search or experiment I/O."""

import numpy as np
import pandas as pd


def calendar_design(index, origin):
    t = np.asarray((index - origin) / pd.Timedelta(hours=1), dtype=float)
    return np.column_stack(
        [
            np.ones(len(t)),
            t / 336,
            *[
                f(2 * np.pi * k * t / period)
                for period in (24, 168)
                for k in (1, 2, 3)
                for f in (np.sin, np.cos)
            ],
        ]
    )


def classical_forecasts(history, times):
    scale = float(history.mean())
    samples = np.array(
        [
            history[
                (history.index.dayofweek == t.dayofweek) & (history.index.hour == t.hour)
            ].values
            for t in times
        ]
    )
    design = calendar_design(history.index, history.index[0])
    beta = np.linalg.lstsq(design, history.values, rcond=None)[0]
    prediction = calendar_design(times, history.index[0]) @ beta
    residuals = history.values - design @ beta
    output = {
        "weekday_empirical": samples,
        "weekly_repeat": samples[:, -1:],
        "all_hour_empirical": np.tile(history.values, (24, 1)),
        "calendar_residual": np.maximum(0, prediction[:, None] + residuals[None, :]),
        "recent_week_empirical": np.tile(history.values[-168:], (24, 1)),
        "recent_day_empirical": np.tile(history.values[-24:], (24, 1)),
        "hour_of_day_empirical": np.array(
            [history[history.index.hour == t.hour].values for t in times]
        ),
        "level_adjusted_weekly": np.maximum(
            0, samples[:, -1:] + history.values[-24:].mean() - history.values[-192:-168].mean()
        ),
    }
    return {p: (v / scale, np.ones(v.shape[1]) / v.shape[1]) for p, v in output.items()}
