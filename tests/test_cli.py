"""Offline CLI uses the primary scorer and preserves invalid-answer penalties."""

import json
import sys

import pytest

from forecast_workflow.cli import main
from forecast_workflow.decision.contract import GRID


@pytest.mark.parametrize("valid", [True, False])
def test_score_cli(tmp_path, monkeypatch, valid):
    contract = dict(
        scale_mw=100,
        capacity_grid_mw=(GRID * 100).tolist(),
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
    (tmp_path / "contract.json").write_text(json.dumps(contract))
    (tmp_path / "actual.json").write_text(json.dumps([100] * 24))
    payload = {"decisions": [{"decision_id": f"b{i:02d}", "value": 100} for i in range(8)]}
    (tmp_path / "answer.txt").write_text(
        "```json\n" + json.dumps(payload) + "\n```" if valid else "{}"
    )
    output = tmp_path / "score.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fwb",
            "score",
            "--contract",
            str(tmp_path / "contract.json"),
            "--actual",
            str(tmp_path / "actual.json"),
            "--answer",
            str(tmp_path / "answer.txt"),
            "--output",
            str(output),
        ],
    )
    main()
    score = json.loads(output.read_text())
    assert score["valid"] is valid
    assert (score["normalized_business_loss"] == 0) is valid


def test_result_ranking_uses_score_not_raw_loss(tmp_path, capsys):
    from forecast_workflow.cli import show_results

    rows = [
        dict(label="Low loss", scored=2, valid=2, loss=0.1, credits=100, score=0.8),
        dict(label="Low score", scored=2, valid=2, loss=0.2, credits=0, score=0.3),
    ]
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            dict(
                version="test",
                case_count=2,
                ranking_metric="score",
                complete=True,
                models=rows,
                fixed_references=[],
            )
        )
    )
    show_results(path)
    output = capsys.readouterr().out
    assert output.index("Low score") < output.index("Low loss")
    assert "S=0.300000" in output
