"""Semantic-preservation and rejection boundaries for the common parser."""

import json

import pytest

from forecast_workflow.evaluation.normalization import normalize_terminal_answer


@pytest.fixture
def payload():
    return {
        "decisions": [{"decision_id": f"b{i:02d}", "value": 1000.125 + i * 0.25} for i in range(8)]
    }


@pytest.mark.parametrize(
    "wrapper",
    ["{}", "```json\n{}\n```", "Explanation.\n```JSON\n{}\n```\nDone.", "Here is the plan: {}"],
)
def test_unambiguous_wrapper_preserves_every_action(payload, wrapper):
    got = normalize_terminal_answer(wrapper.format(json.dumps(payload)))
    assert got.payload == payload and got.rejection is None


@pytest.mark.parametrize("shape", ["array", "map", "numeric_string"])
def test_equivalent_representations(payload, shape):
    if shape == "array":
        candidate = payload["decisions"]
    elif shape == "map":
        candidate = {d["decision_id"]: d["value"] for d in payload["decisions"]}
    else:
        candidate = {"decisions": [d | {"value": str(d["value"])} for d in payload["decisions"]]}
    assert normalize_terminal_answer(json.dumps(candidate)).payload == payload


@pytest.mark.parametrize(
    "change", ["missing", "duplicate_id", "bool", "nan", "units", "comma_number", "unknown_id"]
)
def test_does_not_repair_decisions(payload, change):
    if change == "missing":
        payload["decisions"].pop()
    elif change == "duplicate_id":
        payload["decisions"][-1]["decision_id"] = "b00"
    elif change == "unknown_id":
        payload["decisions"][0]["decision_id"] = "block_0"
    else:
        payload["decisions"][0]["value"] = {
            "bool": True,
            "nan": float("nan"),
            "units": "1000 MW",
            "comma_number": "1,000",
        }[change]
    assert normalize_terminal_answer(json.dumps(payload)).payload is None


def test_multiple_candidates_never_selected_by_value(payload):
    text = json.dumps(payload)
    assert normalize_terminal_answer(text + "\n" + text).rejection == "ambiguous_candidates"


def test_duplicate_json_keys_rejected(payload):
    text = json.dumps(payload).replace('"value": 1000.125', '"value": 1, "value": 1000.125')
    assert normalize_terminal_answer(text).payload is None


def test_malformed_outer_object_never_salvages_inner_plan(payload):
    assert normalize_terminal_answer('{"broken": ' + json.dumps(payload)).payload is None


def test_valid_plan_then_truncated_replacement_rejected(payload):
    assert normalize_terminal_answer(json.dumps(payload) + '\n{"decisions": [').payload is None


def test_tool_argument_wrapper_not_treated_as_submission(payload):
    assert (
        normalize_terminal_answer(json.dumps({"name": "submit", "arguments": payload})).payload
        is None
    )


def test_arithmetic_is_not_evaluated(payload):
    payload["decisions"][0]["value"] = "1000 + 0.125"
    assert normalize_terminal_answer(json.dumps(payload)).payload is None


def test_grid_rounding_is_not_done(payload):
    payload["decisions"][0]["value"] = 1000.123456789
    assert normalize_terminal_answer(json.dumps(payload)).payload == payload


def test_huge_integer_is_rejected_without_crashing(payload):
    payload["decisions"][0]["value"] = 10**500
    assert normalize_terminal_answer(json.dumps(payload)).payload is None


def test_braces_inside_strings_do_not_create_extra_candidates(payload):
    payload["note"] = "Use {braces} as literal metadata"
    result = normalize_terminal_answer("Final: " + json.dumps(payload))
    assert result.payload["decisions"] == payload["decisions"]


def test_no_single_quote_or_trailing_comma_repair(payload):
    assert normalize_terminal_answer(str(payload)).payload is None
    assert normalize_terminal_answer(json.dumps(payload)[:-1] + ",}").payload is None
