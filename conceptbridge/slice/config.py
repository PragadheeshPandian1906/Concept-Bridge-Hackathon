"""Environment-driven configuration for the Slice engine.

All environment parsing happens here. Domain code (``demo/``) must never
read ``os.environ`` directly.

Recognised variables
--------------------
OPENROUTER_API_KEY        API key for OpenRouter (never hard-coded, never printed)
OPENROUTER_BASE_URL       default https://openrouter.ai/api/v1
SLICE_MODEL               primary model
SLICE_FALLBACK_MODEL      used when the primary model fails
SLICE_ESCALATION_MODEL    used when structured-output repair still fails
SLICE_MAX_TOKENS          per-call max_tokens
SLICE_TEMPERATURE         sampling temperature
SLICE_TOKEN_BUDGET        infrastructure token budget for a whole run
SLICE_MAX_ATTEMPTS        infrastructure attempt budget for a whole run
SLICE_TIMEOUT             HTTP timeout in seconds
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_FALLBACK_MODEL = "meta-llama/llama-3.1-8b-instruct"
DEFAULT_ESCALATION_MODEL = "anthropic/claude-3.5-sonnet"


def load_dotenv(path: str | Path = ".env", environ: dict | None = None) -> dict:
    """Load a simple KEY=VALUE .env file into ``environ`` without overwriting.

    Deliberately dependency-free (no python-dotenv required).
    """
    environ = os.environ if environ is None else environ
    p = Path(path)
    if not p.exists():
        return environ
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in environ:
            environ[key] = value
    return environ


def _as_int(value, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _as_float(value, default: float) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Config:
    """Immutable snapshot of the runtime configuration."""

    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    fallback_model: str = DEFAULT_FALLBACK_MODEL
    escalation_model: str = DEFAULT_ESCALATION_MODEL
    max_tokens: int = 900
    temperature: float = 0.2
    token_budget: int = 20000
    max_attempts: int = 8
    timeout: float = 60.0

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def model_chain(self) -> list[str]:
        """Ordered list of models to try: primary -> fallback -> escalation."""
        chain: list[str] = []
        for name in (self.model, self.fallback_model, self.escalation_model):
            if name and name not in chain:
                chain.append(name)
        return chain

    def redacted(self) -> dict:
        """Safe-to-print view. The API key is never included."""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "fallback_model": self.fallback_model,
            "escalation_model": self.escalation_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "token_budget": self.token_budget,
            "max_attempts": self.max_attempts,
            "api_key": "set" if self.has_api_key else "not set",
        }


def load_config(environ: dict | None = None, dotenv: str | Path | None = ".env") -> Config:
    """Build a :class:`Config` from the environment (and optional .env file)."""
    if environ is None:
        if dotenv is not None:
            load_dotenv(dotenv)
        environ = os.environ
    return Config(
        api_key=environ.get("OPENROUTER_API_KEY") or None,
        base_url=environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL),
        model=environ.get("SLICE_MODEL", DEFAULT_MODEL),
        fallback_model=environ.get("SLICE_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
        escalation_model=environ.get("SLICE_ESCALATION_MODEL", DEFAULT_ESCALATION_MODEL),
        max_tokens=_as_int(environ.get("SLICE_MAX_TOKENS"), 900),
        temperature=_as_float(environ.get("SLICE_TEMPERATURE"), 0.2),
        token_budget=_as_int(environ.get("SLICE_TOKEN_BUDGET"), 20000),
        max_attempts=_as_int(environ.get("SLICE_MAX_ATTEMPTS"), 8),
        timeout=_as_float(environ.get("SLICE_TIMEOUT"), 60.0),
    )
