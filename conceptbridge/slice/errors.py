"""Infrastructure-level error types for the Slice engine."""

from __future__ import annotations


class SliceError(Exception):
    """Base class for every error raised by the slice infrastructure."""


class ConfigError(SliceError):
    """Missing or invalid configuration (e.g. no OPENROUTER_API_KEY)."""


class ProviderError(SliceError):
    """The upstream model provider (OpenRouter) failed."""


class LLMError(SliceError):
    """All model attempts, including fallbacks, failed."""


class SchemaError(SliceError):
    """The model returned output that could not be validated."""


class BudgetExceeded(SliceError):
    """Infrastructure token/attempt budget exhausted."""


class StateMachineError(SliceError):
    """Illegal state or transition."""
