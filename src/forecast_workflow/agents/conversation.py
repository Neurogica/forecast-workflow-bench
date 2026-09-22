"""Compact tool responses without changing the information available to agents."""

import json


def compact_conversation(items):
    output = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "function_call_output":
            output.append(item)
            continue
        packet = json.loads(item["output"])
        content = packet.get("content", []) if isinstance(packet, dict) else []
        if (
            isinstance(packet, dict)
            and "structuredContent" in packet
            and len(content) == 1
            and content[0].get("type") == "text"
        ):
            try:
                if json.loads(content[0]["text"]) == packet["structuredContent"]:
                    packet = {k: v for k, v in packet.items() if k != "content"}
            except (ValueError, KeyError, TypeError):
                pass
        output.append(
            item | dict(output=json.dumps(packet, separators=(",", ":"), allow_nan=False))
        )
    return output
