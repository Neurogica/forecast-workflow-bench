import pytest

from forecast_workflow.evaluation.oracle import Candidate, frontier, matched_gap, select


def test_frontier_and_budget_boundary():
    menu = [
        Candidate("free", 0.1, 0),
        Candidate("dominated", 0.12, 4),
        Candidate("paid", 0.05, 10),
        Candidate("waste", 0.05, 20),
    ]
    assert [c.name for c in frontier(menu)] == ["free", "paid"]
    assert select(menu, 9).name == "free"
    assert select(menu, 10).name == "paid"
    assert select(menu, 20).name == "paid"
    assert matched_gap(0.04, 10, menu) == pytest.approx(-0.01)


def test_casewise_dominance_and_credit_penalty():
    menu = [Candidate("free", 0.1, 0), Candidate("paid", 0.05, 10)]
    for loss in [0.03, 0.07, 0.2]:
        for spent in range(21):
            assert matched_gap(loss, spent, menu) <= matched_gap(loss + 0.01, spent, menu)
            if spent:
                assert matched_gap(loss, spent - 1, menu) <= matched_gap(loss, spent, menu)
    assert matched_gap(0.1, 0, menu) < matched_gap(0.1, 10, menu)


def test_invalid_inputs_are_not_silently_coerced():
    with pytest.raises(ValueError):
        Candidate("bad", float("nan"), 0)
    with pytest.raises(ValueError):
        Candidate("bad", 0.1, -1)
    with pytest.raises(ValueError):
        select([Candidate("paid", 0.1, 2)], 1)
    with pytest.raises(ValueError):
        select([Candidate("free", 0.1, 0)], 1.5)


def test_cost_aware_gap_penalizes_spending_on_flat_oracle_frontier():
    from forecast_workflow.evaluation.oracle import cost_aware_gap

    menu = [Candidate("free", 0.1, 0), Candidate("paid", 0.05, 10)]
    assert matched_gap(0.07, 10, menu) == matched_gap(0.07, 20, menu)
    assert cost_aware_gap(0.07, 20, menu, 100, 0.2) - cost_aware_gap(
        0.07, 10, menu, 100, 0.2
    ) == pytest.approx(0.02)


def test_cost_aware_oracle_can_trade_accuracy_for_cost():
    from forecast_workflow.evaluation.oracle import cost_aware_gap, select_cost_aware

    menu = [Candidate("free", 0.1, 0), Candidate("paid", 0.05, 100)]
    assert select_cost_aware(menu, 100, 0.01).name == "paid"
    assert select_cost_aware(menu, 100, 0.2).name == "free"
    assert cost_aware_gap(0.1, 0, menu, 100, 0.2) == 0
    assert cost_aware_gap(0.04, 0, menu, 100, 0.2) == pytest.approx(-0.06)


def test_common_oracle_preserves_objective_differences():
    from forecast_workflow.evaluation.oracle import cost_aware_gap

    menu = [Candidate("free", 0.1, 0), Candidate("paid", 0.05, 100)]
    a = cost_aware_gap(0.05, 100, menu, 100, 0.2)
    b = cost_aware_gap(0.1, 0, menu, 100, 0.2)
    assert a - b == pytest.approx(0.15)
    with pytest.raises(ValueError):
        cost_aware_gap(0.05, 101, menu, 100, 0.2)
    with pytest.raises(ValueError):
        cost_aware_gap(0.05, 0, menu, 0, 0.2)
    with pytest.raises(ValueError):
        cost_aware_gap(0.05, 0, menu, 100, -1)


def test_cost_gap_strict_dominance_and_exchange_rate():
    from forecast_workflow.evaluation.oracle import cost_aware_gap

    menu = [Candidate("free", 0.06, 0), Candidate("paid", 0.04, 50000)]
    budget, weight = 113726, 0.01
    base = cost_aware_gap(0.05, 10000, menu, budget, weight)
    assert cost_aware_gap(0.049, 10000, menu, budget, weight) < base
    assert cost_aware_gap(0.05, 9999, menu, budget, weight) < base
    assert cost_aware_gap(0.049, 9999, menu, budget, weight) < base
    extra = cost_aware_gap(0.05, 20000, menu, budget, weight)
    assert extra - base == pytest.approx(weight * 10000 / budget)
    # A small loss improvement does not compensate for spending the full budget.
    assert cost_aware_gap(0.05, 0, menu, budget, weight) < cost_aware_gap(
        0.049, budget, menu, budget, weight
    )
