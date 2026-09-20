"""Provider-neutral runtime boundary for structured LLM calls."""

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """Raised when a required model call cannot produce valid output."""


class OpenRouterClient:
    """Bounded OpenRouter gateway used by domain agents.

    The runtime never silently turns a failed request into an answer. Domain
    agents decide whether to use a deterministic fallback or propagate this
    exception according to their policy.
    """

    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, settings):
        self.settings = settings

    def structured(self, system: str, user: str, output_model: type[T]) -> T:
        if self.settings.demo_mode:
            raise LLMUnavailable("LLM is disabled by CONCEPTBRIDGE_DEMO_MODE=true")
        if not self.settings.openrouter_api_key:
            raise LLMUnavailable("OPENROUTER_API_KEY is not configured")

        errors: list[str] = []
        models = dict.fromkeys([self.settings.llm_model, self.settings.llm_fallback_model])
        for model in models:
            try:
                response = httpx.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": self.settings.llm_max_tokens,
                    },
                    timeout=self.settings.llm_timeout,
                )
                response.raise_for_status()
                choice = response.json()["choices"][0]
                content = choice["message"]["content"]
                if choice.get("finish_reason") == "length":
                    raise ValueError("provider truncated the structured response at max_tokens")
                return output_model.model_validate(json.loads(content))
            except Exception as exc:
                errors.append(f"{model}: {exc}")
        raise LLMUnavailable("OpenRouter structured call failed: " + " | ".join(errors))