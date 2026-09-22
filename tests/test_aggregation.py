import pytest

from forecast_workflow.evaluation.aggregation import case_weights, complete_weighted_mean


def test_dates_do_not_reweight_series_or_domains():
    cases = [
        dict(case_id="a1", cohort="power", authority="a", family="day"),
        dict(case_id="a2", cohort="power", authority="a", family="day"),
        dict(case_id="b1", cohort="power", authority="b", family="week"),
        dict(case_id="c1", cohort="bike", authority="c", family="day"),
    ]
    weights = case_weights(cases, {"power": 0.5, "bike": 0.5})
    assert weights == {"a1": 0.125, "a2": 0.125, "b1": 0.25, "c1": 0.5}
    assert complete_weighted_mean(dict(a1=0, a2=0, b1=4, c1=2), weights) == 2
    with pytest.raises(ValueError, match="complete frozen"):
        complete_weighted_mean(dict(a1=0, b1=4, c1=2), weights)


def test_bad_indexes_and_weights_are_rejected():
    case = dict(case_id="a", cohort="power", authority="a", family="day")
    with pytest.raises(ValueError, match="unique"):
        case_weights([case, case], {"power": 1.0})
    with pytest.raises(ValueError, match="exactly"):
        case_weights([case], {"other": 1.0})
    with pytest.raises(ValueError, match="sum"):
        case_weights([case], {"power": 0.5})
    with pytest.raises(ValueError, match="finite"):
        complete_weighted_mean({"a": float("nan")}, {"a": 1.0})
