"""Deterministic, gold-blind terminal-answer normalization (format-v1).

No execution, tool access, numeric rounding, ID inference, or candidate selection.
Kept outside the frozen online evaluator so live generations remain comparable.
"""

import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

VERSION = "format-v1"
IDS = tuple(f"b{i:02d}" for i in range(8))
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


class FormatError(ValueError):
    pass


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise FormatError("duplicate_json_key")
        out[key] = value
    return out


def _constant(value):
    raise FormatError("nonfinite_json_number")


DECODER = json.JSONDecoder(object_pairs_hook=_pairs, parse_constant=_constant)


@dataclass(frozen=True)
class NormalizedAnswer:
    payload: dict | None
    operations: tuple[str, ...]
    rejection: str | None = None


def _canonical(value, ids):
    operations = []
    if isinstance(value, dict) and "decisions" in value:
        entries = value["decisions"]
        # Additional forecast metadata does not affect operational actions.
    elif isinstance(value, list):
        entries = value
        operations.append("bare_decision_array")
    elif isinstance(value, dict) and set(value) == set(ids):
        entries = [{"decision_id": k, "value": v} for k, v in value.items()]
        operations.append("id_value_object")
    else:
        raise FormatError("not_a_decision_submission")
    if not isinstance(entries, list) or len(entries) != len(ids):
        raise FormatError("missing_or_extra_decisions")
    output = []
    for entry in entries:
        if not isinstance(entry, dict) or not {"decision_id", "value"} <= entry.keys():
            raise FormatError("missing_decision_fields")
        key, number = entry["decision_id"], entry["value"]
        if not isinstance(key, str) or key not in ids:
            raise FormatError("unknown_decision_id")
        if isinstance(number, str):
            if not NUMBER.fullmatch(number):
                raise FormatError("not_a_numeric_literal")
            # This is the same numeric conversion used for a JSON number token.
            try:
                Decimal(number)  # Explicitly reject non-decimal syntaxes.
                number = json.loads(number)
            except (ValueError, InvalidOperation):
                raise FormatError("not_a_numeric_literal") from None
            operations.append("quoted_numeric_literal")
        try:
            finite = type(number) in (int, float) and math.isfinite(number)
        except OverflowError:
            finite = False
        if not finite:
            raise FormatError("nonfinite_or_nonnumeric_action")
        output.append({"decision_id": key, "value": number})
    if len({e["decision_id"] for e in output}) != len(ids):
        raise FormatError("duplicate_decision_id")
    return {"decisions": output}, tuple(dict.fromkeys(operations))


def _segment_end(text, start):
    """Skip an entire malformed candidate, never salvage a nested object."""
    stack = []
    quoted = escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch in "[{":
            stack.append(ch)
        elif ch in "]}":
            if not stack or stack.pop() != {"]": "[", "}": "{"}[ch]:
                return index + 1
            if not stack:
                return index + 1
    return len(text)


def normalize_terminal_answer(text: str, ids=IDS) -> NormalizedAnswer:
    """Return a canonical answer only when one complete JSON value is unambiguous."""
    if not isinstance(text, str):
        return NormalizedAnswer(None, (), "nontext_response")
    text = text.strip().lstrip("\ufeff").strip()
    if not text:
        return NormalizedAnswer(None, (), "empty_response")
    try:
        value, end = DECODER.raw_decode(text)
        if not text[end:].strip():
            payload, operations = _canonical(value, ids)
            return NormalizedAnswer(payload, operations)
    except FormatError as exc:
        return NormalizedAnswer(None, (), str(exc))
    except (json.JSONDecodeError, ValueError):
        pass
    candidates = []
    malformed = False
    index = 0
    while index < len(text):
        ch = text[index]
        # Avoid treating ordinary prose intervals [0,24) as JSON containers.
        if ch != "{" and not (ch == "[" and text[index + 1 :].lstrip().startswith("{")):
            index += 1
            continue
        try:
            value, end = DECODER.raw_decode(text, index)
            candidates.append(value)
            index = end
        except (json.JSONDecodeError, FormatError, ValueError):
            end = _segment_end(text, index)
            fragment = text[index:end]
            if any(token in fragment for token in ['"decisions"', '"decision_id"', '"b00"']):
                malformed = True
            index = max(end, index + 1)
    if malformed:
        return NormalizedAnswer(None, (), "malformed_decision_candidate")
    if len(candidates) != 1:
        return NormalizedAnswer(
            None, (), "ambiguous_candidates" if candidates else "no_complete_json"
        )
    try:
        payload, operations = _canonical(candidates[0], ids)
    except FormatError as exc:
        return NormalizedAnswer(None, (), str(exc))
    fence = re.fullmatch(r"```(?:json)?\s*\n.*?\n```", text, re.DOTALL | re.IGNORECASE)
    wrapper = "whole_json_fence" if fence else "unique_json_in_text"
    return NormalizedAnswer(payload, (wrapper,) + operations)
