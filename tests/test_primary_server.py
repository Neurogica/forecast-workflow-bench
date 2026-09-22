"""Primary tool wiring, free-plan feasibility and charged coverage errors."""

import json

import numpy as np
import pytest

from forecast_workflow.core.io import write_json
from forecast_workflow.decision.contract import GRID
from forecast_workflow.evaluation.grading import grade
from forecast_workflow.tools.server import CLASSICAL, TOOLS, make_server


def unpack(result):
    if isinstance(result, dict):
        return result
    if isinstance(result, tuple):
        return result[1]
    return json.loads(result[0].text)


@pytest.fixture
def primary(catalog_dir, monkeypatch):
    contract = dict(
        scale_mw=360.0,
        capacity_grid_mw=(GRID * 360).tolist(),
        target_start="2026-01-31T00:00:00Z",
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
    write_json(catalog_dir / "business_contract.json", contract)
    write_json(catalog_dir / "probabilistic_forecasts.json", {"models": ["seasonal_empirical"]})
    write_json(
        catalog_dir / "forecast_budget.json",
        dict(
            profile_id="fixture",
            unit="test credits",
            budget=20,
            evidence_sha256="fixture",
            rates=[
                dict(
                    model="seasonal_empirical_quantiles",
                    context_limit=1000,
                    horizon_limit=336,
                    credits=5,
                )
            ],
        ),
    )
    ledger = catalog_dir / "ledger.json"
    monkeypatch.setenv("FWB_BUDGET_LOG", str(ledger))
    return make_server(catalog_dir, "2026-01-30T23:00:00Z"), contract, ledger


async def test_primary_catalog_and_free_plans(primary):
    server, contract, _ = primary
    assert {t.name for t in await server.list_tools()} == set(TOOLS)
    for method in CLASSICAL:
        response = unpack(
            await server.call_tool("classical_plan", {"series_id": "fixture", "method": method})
        )
        assert response["forecast_credits"] == 0
        assert grade(response["capacity_plan"]["submission"], contract, [360] * 24)["valid"]
    budget = unpack(await server.call_tool("budget_status", {}))
    assert budget["spent"] == 0


async def test_primary_charges_forecast_even_when_target_coverage_fails(primary):
    server, contract, ledger = primary
    args = dict(series_id="fixture", model="seasonal_empirical", context_steps=336, horizon=12)
    with pytest.raises(Exception, match="cover|target|hour"):
        await server.call_tool("forecast_and_plan", args)
    assert json.loads(ledger.read_text())["spent"] == 5
    args["horizon"] = 24
    result = unpack(await server.call_tool("forecast_and_plan", args))
    assert grade(result["capacity_plan"]["submission"], contract, np.full(24, 360))["valid"]
    assert json.loads(ledger.read_text())["spent"] == 10


async def test_bounded_episode_uses_reorganized_primary_server(primary, catalog_dir):
    """Real MCP subprocess with a fake language model; no API or TSFM download."""
    from types import SimpleNamespace

    from forecast_workflow.agents.runtime import episode
    from forecast_workflow.core.schema import Task

    class Client:
        def __init__(self):
            self.responses = self
            self.requests = 0

        async def create(self, **kwargs):
            self.requests += 1
            if self.requests == 1:
                output = [
                    SimpleNamespace(
                        type="function_call",
                        name="classical_plan",
                        call_id="fixture-call",
                        arguments=json.dumps({"series_id": "fixture", "method": "weekly_repeat"}),
                    )
                ]
                text = ""
            else:
                output = []
                text = json.dumps(
                    {"decisions": [{"decision_id": f"b{i:02d}", "value": 360} for i in range(8)]}
                )
            return SimpleNamespace(
                model="fixture-model",
                id="fixture",
                status="completed",
                usage=None,
                output=output,
                output_text=text,
            )

    task = Task(
        task_id="fixture",
        group_id="fixture",
        split="dev",
        family="decision_flexible_day_ahead",
        instruction="Synthetic test only",
        as_of="2026-01-30T23:00:00Z",
        max_calls=12,
        allowed_tools=TOOLS,
    )
    trace = []
    result = await episode(task, catalog_dir, Client(), "fixture-model", None, trace)
    assert result["status"] == "completed"
    assert result["tool_calls"] == 1
    assert result["returned_models"] == ["fixture-model"]
