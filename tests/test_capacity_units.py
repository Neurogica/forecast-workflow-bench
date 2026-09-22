"""Unit migration must preserve decisions and reject ambiguous contracts."""

import numpy as np
import pytest

from forecast_workflow.decision.contract import GRID
from forecast_workflow.decision.optimizer import optimize_marginals
from forecast_workflow.decision.units import capacity_units
from forecast_workflow.evaluation.grading import grade


def test_transport_zero_counts_and_legacy_results_are_unit_invariant():
    terms = dict(
        billing="imbalance",
        block_hours=3,
        reservation=0.3,
        shortage=1,
        emergency=0,
        emergency_buffer=0.1,
        adjustment=0,
        ramp=0.3,
        hourly_priority=[1] * 24,
    )
    actual = np.repeat([0, 2, 5, 8, 6, 5, 2, 0], 3)
    transport = dict(
        scale=4, capacity_grid=(GRID * 4).tolist(), unit="departures/hour", terms=terms
    )
    legacy = dict(scale_mw=400, capacity_grid_mw=(GRID * 400).tolist(), terms=terms)
    new = optimize_marginals(actual[:, None], [1], transport)
    old = optimize_marginals(actual[:, None] * 100, [1], legacy)
    assert grade(new["submission"], transport, actual)["valid"]
    assert grade(new["submission"], transport, actual)["normalized_business_loss"] == pytest.approx(
        grade(old["submission"], legacy, actual * 100)["normalized_business_loss"]
    )
    np.testing.assert_allclose(
        [d["value"] * 100 for d in new["submission"]["decisions"]],
        [d["value"] for d in old["submission"]["decisions"]],
    )


@pytest.mark.parametrize("unit", [None, "", "departures/hour"])
def test_ambiguous_unit_aliases_are_rejected(unit):
    contract = dict(
        scale=1, capacity_grid=GRID.tolist(), unit=unit, scale_mw=1, capacity_grid_mw=GRID.tolist()
    )
    with pytest.raises(ValueError):
        capacity_units(contract)
