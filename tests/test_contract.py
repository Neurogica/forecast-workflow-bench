"""Independent exact-enumeration and billing checks for the development optimizer."""

from itertools import product

import numpy as np
import pytest

from forecast_workflow.decision import contract as flexible


def terms(**overrides):
    return dict(
        block_hours=6,
        reservation=0.6,
        shortage=1.0,
        emergency=2.0,
        emergency_buffer=0.1,
        ramp=0.2,
        adjustment=1.0,
        hourly_priority=[1.0] * 24,
        **overrides,
    )


def test_dynamic_program_matches_exhaustive_search(monkeypatch):
    monkeypatch.setattr(flexible, "GRID", np.array([0.8, 1.0, 1.2]))
    cost = np.random.default_rng(10).uniform(size=(24, 3))
    contract = terms()
    exact = flexible.optimize(cost, contract)
    enumerated = []
    for blocks in product(range(3), repeat=4):
        capacities = flexible.GRID[list(blocks)]
        if np.any(np.abs(np.diff(capacities)) > 0.2 + 1e-10):
            continue
        actions = np.repeat(blocks, 6)
        # Independent objective; do not use the production scorer as the oracle.
        enumerated.append(
            (sum(cost[h, actions[h]] for h in range(24)) + sum(abs(np.diff(capacities)))) / 24
        )
    assert flexible.realized_loss(cost, exact, contract) == pytest.approx(min(enumerated))


def test_imbalance_billing_charges_only_surplus_or_shortage(monkeypatch):
    monkeypatch.setattr(flexible, "GRID", np.array([0.8, 1.0, 1.2]))
    cost = flexible.hourly_cost(np.ones((24, 1)), np.ones(1), terms(billing="imbalance"))
    np.testing.assert_allclose(cost[0], [0.2 + 2 * 0.1, 0.0, 0.6 * 0.2], atol=1e-12)


def test_marginal_mixture_preserves_expected_loss():
    contract = terms(billing="imbalance")
    a, b = np.full((24, 1), 0.8), np.full((24, 1), 1.2)
    np.testing.assert_allclose(
        flexible.hourly_cost(np.concatenate([a, b], axis=1), [0.25, 0.75], contract),
        0.25 * flexible.hourly_cost(a, [1.0], contract)
        + 0.75 * flexible.hourly_cost(b, [1.0], contract),
    )


def test_infeasible_hourly_changes_are_rejected():
    with pytest.raises(ValueError, match="Infeasible"):
        flexible.realized_loss(np.ones((24, len(flexible.GRID))), np.arange(24), terms())
