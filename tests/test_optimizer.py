"""Optimizer control semantics on synthetic forecasts, never private observations."""

import pandas as pd
import pytest

from forecast_workflow.decision.optimizer import GRID, LEVELS, plan_packet  # noqa: E402


def fixture():
    contract = dict(
        scale_mw=100,
        capacity_grid_mw=(GRID * 100).tolist(),
        target_start="2026-09-02T00:00:00Z",
        terms=dict(
            billing="imbalance",
            block_hours=3,
            reservation=0.3,
            shortage=1,
            emergency=0,
            emergency_buffer=0.1,
            adjustment=0,
            ramp=0.3,
            hourly_priority=[1] * 24,
        ),
    )
    packet = dict(
        hours=1,
        timestamp=[
            t.isoformat() for t in pd.date_range("2026-09-01T00:00:00Z", periods=48, freq="h")
        ],
        quantiles={str(q): [50] * 24 + [100] * 24 for q in LEVELS},
    )
    return packet, contract


def test_control_selects_target_not_forecast_prefix():
    packet, contract = fixture()
    result = plan_packet(packet, contract)
    assert [d["value"] for d in result["submission"]["decisions"]] == [100] * 8
    assert result["expected_normalized_loss"] == 0


@pytest.mark.parametrize("change", ["short", "coarse", "missing_quantile"])
def test_control_rejects_unsupported_information(change):
    packet, contract = fixture()
    if change == "short":
        packet["timestamp"] = packet["timestamp"][:-1]
    elif change == "coarse":
        packet["hours"] = 3
    else:
        del packet["quantiles"]["0.1"]
    with pytest.raises(ValueError):
        plan_packet(packet, contract)
