"""Structured output: extraction, validation and schema repair.

Model prose is never trusted. Every important model output is parsed into
a typed model. If validation fails once, a repair attempt is made with the
validation error fed back to the model. If that also fails we raise
:class:`SchemaError` - we never fabricate a plausible object.
"""

from __future__ import annotations

import json
import typing
from typing import Any, get_args, get_origin

from .budget import Budget
from .compat import BaseModel, ValidationError
from .config import Config, load_config
from .errors import LLMError, SchemaError
from .llm import complete


# ---------------------------------------------------------------- JSON
def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response."""
    if text is None:
        raise SchemaError("empty model response")
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    if start == -1:
        raise SchemaError(f"no JSON object found in model response: {raw[:160]!r}")
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(raw)):
        char = raw[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                chunk = raw[start:index + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError as exc:
                    raise SchemaError(f"malformed JSON object: {exc}")
    raise SchemaError("unterminated JSON object in model response")


# -------------------------------------------------------------- schema
def _describe(annotation) -> str:
    origin = get_origin(annotation)
    if origin in (list, tuple):
        args = get_args(annotation)
        inner = _describe(args[0]) if args else "any"
        return f"[{inner}, ...]"
    if origin is typing.Union or str(origin) == "<class 'types.UnionType'>":
        return " | ".join(_describe(a) for a in get_args(annotation) if a is not type(None))
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return schema_hint(annotation)
    return {str: '"string"', float: "0.0", int: "0", bool: "true"}.get(annotation, '"value"')


def schema_hint(model_cls: type) -> str:
    """Human/model readable JSON skeleton for a model class."""
    hints = typing.get_type_hints(model_cls)
    fields = getattr(model_cls, "model_fields", None) or getattr(
        model_cls, "__fields_def__", {}
    )
    parts = []
    for name in fields:
        if name.startswith("_"):
            continue
        parts.append(f'  "{name}": {_describe(hints.get(name, Any))}')
    return "{\n" + ",\n".join(parts) + "\n}"


def validate_into(model_cls: type, data: Any):
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise SchemaError(str(exc))


REPAIR_TEMPLATE = """Your previous response could not be parsed.

Error:
{error}

Return ONLY a valid JSON object matching exactly this shape (no prose,
no markdown fences, no extra keys):

{schema}
"""


def complete_structured(
    prompt: str,
    model_cls: type,
    *,
    system: str | None = None,
    config: Config | None = None,
    budget: Budget | None = None,
    provider=None,
    label: str = "structured",
    repair: bool = True,
    on_event=None,
):
    """Complete, then parse into ``model_cls``. One repair attempt allowed."""
    config = config or load_config()
    schema = schema_hint(model_cls)
    full_prompt = (
        f"{prompt}\n\nReturn ONLY a JSON object with exactly this shape:\n{schema}"
    )

    try:
        result = complete(
            full_prompt, system=system, config=config, budget=budget,
            provider=provider, label=label, on_event=on_event,
        )
    except LLMError:
        raise

    try:
        return validate_into(model_cls, extract_json(result.text))
    except SchemaError as first_error:
        if on_event:
            on_event({"event": "schema_invalid", "label": label, "error": str(first_error)})
        if not repair:
            raise
        repair_prompt = full_prompt + "\n\n" + REPAIR_TEMPLATE.format(
            error=str(first_error), schema=schema
        )
        try:
            retry = complete(
                repair_prompt, system=system, config=config, budget=budget,
                provider=provider, label=f"{label}:repair", on_event=on_event,
            )
        except LLMError as exc:
            raise SchemaError(f"repair attempt failed: {exc}")
        try:
            return validate_into(model_cls, extract_json(retry.text))
        except SchemaError as second_error:
            raise SchemaError(
                f"structured output invalid after repair: {second_error}"
            )
