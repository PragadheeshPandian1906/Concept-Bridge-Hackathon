"""LLM gateway.

This is the ONLY module in the repository that is allowed to talk HTTP to
OpenRouter. Domain code calls :func:`complete` and never builds requests.

A *provider* is a small object with::

    complete(messages, model, config) -> LLMResult

``OpenRouterProvider`` is the real one. ``demo/conceptbridge/stub.py``
supplies a deterministic provider so the identical flow runs offline; the
provider is the only thing that changes between stub mode and live mode.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .budget import Budget
from .config import Config, load_config
from .errors import ConfigError, LLMError, ProviderError


@dataclass
class LLMResult:
    """One successful completion."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    provider: str = "openrouter"
    raw: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def estimate_tokens(text: str) -> int:
    """Crude but deterministic token estimate (~4 characters per token)."""
    return max(1, len(text or "") // 4)


class OpenRouterProvider:
    """Real provider: POST /chat/completions on OpenRouter."""

    name = "openrouter"

    def complete(self, messages: list[dict], model: str, config: Config) -> LLMResult:
        if not config.has_api_key:
            raise ConfigError(
                "OPENROUTER_API_KEY is not set. Export it, put it in .env, "
                "or run with --stub."
            )
        body = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }).encode("utf-8")

        request = urllib.request.Request(
            url=f"{config.base_url.rstrip('/')}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost/conceptbridge",
                "X-Title": "ConceptBridge",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=config.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise ProviderError(f"OpenRouter HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenRouter unreachable: {exc.reason}") from None
        except Exception as exc:  # pragma: no cover - defensive
            raise ProviderError(f"OpenRouter call failed: {exc}") from None

        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"Unexpected OpenRouter payload: {str(payload)[:300]}")

        usage = payload.get("usage") or {}
        return LLMResult(
            text=text or "",
            model=payload.get("model", model),
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            provider=self.name,
            raw={"id": payload.get("id")},
        )


_DEFAULT_PROVIDER = OpenRouterProvider()


def complete(
    prompt: str,
    *,
    system: str | None = None,
    config: Config | None = None,
    budget: Budget | None = None,
    provider=None,
    label: str = "llm",
    on_event=None,
) -> LLMResult:
    """Run one completion, walking the model chain on failure.

    Tries ``config.model``, then ``fallback_model``, then
    ``escalation_model``. Charges the budget for every attempt. Raises
    :class:`LLMError` when every model in the chain fails.
    """
    config = config or load_config()
    budget = budget or Budget.from_config(config)
    provider = provider or _DEFAULT_PROVIDER

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    errors: list[str] = []
    for index, model in enumerate(config.model_chain()):
        budget.start_attempt(f"{label}:{model}")
        try:
            result = provider.complete(messages, model, config)
        except (ProviderError, ConfigError) as exc:
            errors.append(f"{model}: {exc}")
            if on_event:
                on_event({"event": "model_failed", "model": model, "error": str(exc)})
            continue

        tokens = result.total_tokens or (
            estimate_tokens(prompt) + estimate_tokens(result.text)
        )
        result.prompt_tokens = result.prompt_tokens or estimate_tokens(prompt)
        result.completion_tokens = result.completion_tokens or estimate_tokens(result.text)
        budget.charge(tokens)
        if on_event:
            on_event({
                "event": "model_ok",
                "model": result.model,
                "tokens": tokens,
                "fallback": index > 0,
                "label": label,
            })
        return result

    raise LLMError("all models failed -> " + " | ".join(errors))
