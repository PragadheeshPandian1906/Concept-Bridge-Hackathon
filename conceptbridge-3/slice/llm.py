"""The only place in the codebase that talks to OpenRouter.

Domain agents call ``complete(...)`` with a Pydantic schema and get back a
validated object, or a typed error. They never build HTTP requests themselves.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .budget import Budget
from .config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    """Base class for every controlled LLM failure."""


class ModelError(LLMError):
    """The provider failed for both the primary and the fallback model."""


class SchemaFailure(LLMError):
    """The model answered, but never in the required shape."""


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
    if start == -1:
        raise SchemaFailure("no JSON object found in model output")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


def _call_openrouter(settings: Settings, model: str, messages: list[dict]) -> tuple[str, int]:
    import httpx

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": settings.max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "X-Title": "ConceptBridge",
    }
    try:
        response = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=settings.timeout)
    except Exception as exc:  # network/timeout
        raise ModelError(f"OpenRouter request failed for {model}: {exc}") from exc
    if response.status_code >= 400:
        raise ModelError(f"OpenRouter {response.status_code} for {model}: {response.text[:200]}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise ModelError(f"unexpected OpenRouter payload: {str(data)[:200]}") from exc
    tokens = int(data.get("usage", {}).get("total_tokens", 0))
    return content, tokens


def complete(
    *,
    messages: list[dict],
    schema: Type[T],
    step: str,
    stub: Callable[[], dict] | None = None,
    settings: Settings | None = None,
    budget: Budget | None = None,
) -> T:
    """Return a validated ``schema`` instance.

    In DEMO_MODE (or without an API key) the deterministic ``stub`` is used, so
    the whole state machine can be exercised offline.
    """
    settings = settings or get_settings()
    budget = budget or Budget()
    budget.check(step)

    if settings.demo_mode:
        if stub is None:
            raise ModelError(f"DEMO_MODE is on but step '{step}' has no stub")
        budget.record(step, 0)
        return schema.model_validate(stub())

    attempts: list[str] = [settings.model, settings.fallback_model]
    last_error: Exception | None = None
    for model in attempts:
        try:
            content, tokens = _call_openrouter(settings, model, messages)
            budget.record(step, tokens)
        except ModelError as exc:
            last_error = exc
            continue
        for repair in (False, True):
            try:
                return schema.model_validate(_extract_json(content))
            except (ValidationError, json.JSONDecodeError, SchemaFailure) as exc:
                last_error = exc
                if repair:
                    break
                budget.check(step)
                repair_messages = messages + [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": (
                            "That output did not match the required JSON schema. "
                            f"Error: {exc}. Return ONLY a valid JSON object matching:\n"
                            f"{json.dumps(schema.model_json_schema())}"
                        ),
                    },
                ]
                try:
                    content, tokens = _call_openrouter(settings, model, repair_messages)
                    budget.record(step + ":repair", tokens)
                except ModelError as repair_exc:
                    last_error = repair_exc
                    break
    raise SchemaFailure(f"step '{step}' produced no valid structured output: {last_error}")
