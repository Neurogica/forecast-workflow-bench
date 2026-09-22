"""Local transport preserves tool-call identity and rejects hosted inference endpoints."""

import json

import pytest

from forecast_workflow.agents.local import LocalClient, Record, messages_for  # noqa: E402


def test_roundtrip_retains_assistant_and_tool_result():
    packet = {"structuredContent": {"x": 42}, "content": [{"type": "text", "text": '{"x":42}'}]}
    msgs = messages_for(
        "same instruction",
        [
            {"role": "user", "content": "task"},
            Record(
                type="function_call",
                call_id="c1",
                name="history",
                arguments="{}",
                assistant_content="Checking observed history.",
            ),
            {"type": "function_call_output", "call_id": "c1", "output": json.dumps(packet)},
        ],
    )
    assert msgs[0]["content"] == "same instruction"
    assert msgs[2]["tool_calls"][0]["id"] == msgs[3]["tool_call_id"] == "c1"
    assert msgs[2]["content"] == "Checking observed history."
    assert json.loads(msgs[3]["content"]) == {"structuredContent": {"x": 42}}


@pytest.mark.parametrize("url", ["https://api.openai.com", "http://example.com", "ftp://localhost"])
def test_remote_inference_is_disallowed(url):
    with pytest.raises(ValueError, match="loopback"):
        LocalClient(url, 1, [])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,is_context",
    [
        ("request exceeds context size", True),
        ("invalid tool schema", False),
    ],
)
async def test_only_context_exhaustion_is_a_capability_limit(monkeypatch, message, is_context):
    import httpx

    from forecast_workflow.agents.local import LocalContextLimit

    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(400, text=message))
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )
    expected = LocalContextLimit if is_context else httpx.HTTPStatusError
    with pytest.raises(expected):
        await LocalClient("http://127.0.0.1:1", 1, []).create(
            model="test", instructions="test", input=[], tools=[], max_output_tokens=10
        )
