"""Local-only chat transport for the unchanged MCP episode loop; no hosted API fallback."""

from types import SimpleNamespace
from urllib.parse import urlparse

import httpx

from forecast_workflow.agents.conversation import compact_conversation


class Record(SimpleNamespace):
    def model_dump(self, **kwargs):
        return vars(self)


class LocalContextLimit(ValueError):
    """The fixed local context window was exhausted; do not retry or truncate."""


def messages_for(instructions, items):
    messages = [dict(role="system", content=instructions)]
    for item in compact_conversation(items):
        x = item if isinstance(item, dict) else vars(item)
        kind = x.get("type")
        if kind == "function_call":
            messages.append(
                dict(
                    role="assistant",
                    content=x.get("assistant_content"),
                    tool_calls=[
                        dict(
                            id=x["call_id"],
                            type="function",
                            function=dict(name=x["name"], arguments=x["arguments"]),
                        )
                    ],
                )
            )
        elif kind == "function_call_output":
            messages.append(dict(role="tool", tool_call_id=x["call_id"], content=x["output"]))
        elif kind == "message":
            messages.append(dict(role="assistant", content=x["text"]))
        elif x.get("role") in ("user", "assistant"):
            messages.append(dict(role=x["role"], content=x["content"]))
        else:
            raise ValueError("Unsupported local conversation item")
    return messages


class LocalClient:
    def __init__(self, endpoint, seed, audit):
        parsed = urlparse(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("Only loopback inference endpoints are allowed")
        self.endpoint, self.seed, self.audit = endpoint, seed, audit
        self.responses = self

    async def create(self, **kwargs):
        body = dict(
            model=kwargs["model"],
            messages=messages_for(kwargs["instructions"], kwargs["input"]),
            tools=[
                dict(
                    type="function",
                    function={k: t[k] for k in ("name", "description", "parameters")},
                )
                for t in kwargs["tools"]
            ],
            parallel_tool_calls=False,
            max_tokens=kwargs["max_output_tokens"],
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            seed=self.seed,
            chat_template_kwargs=dict(enable_thinking=False),
        )
        async with httpx.AsyncClient(timeout=900, trust_env=False) as client:
            response = await client.post(self.endpoint + "/v1/chat/completions", json=body)
            if response.status_code == 400:
                error = response.text.lower()
                if "context" in error and ("exceed" in error or "too large" in error):
                    raise LocalContextLimit("Local context budget exhausted")
            response.raise_for_status()
            data = response.json()
        self.audit.append(data)
        choice = data["choices"][0]
        msg = choice["message"]
        calls = msg.get("tool_calls") or []
        output = [
            Record(
                type="function_call",
                call_id=c["id"],
                name=c["function"]["name"],
                arguments=c["function"]["arguments"],
                assistant_content=msg.get("content") if index == 0 else None,
            )
            for index, c in enumerate(calls)
        ]
        text = msg.get("content") or ""
        if not output:
            output = [Record(type="message", text=text)]
        u = data.get("usage", {})
        return Record(
            id=data["id"],
            model=data.get("model", kwargs["model"]),
            status=choice["finish_reason"],
            output=output,
            output_text=text,
            usage=Record(
                input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0)
            ),
        )
