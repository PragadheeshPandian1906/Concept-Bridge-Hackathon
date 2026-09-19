"""Agentic Slice Kit - reusable agent infrastructure.

This package is domain-agnostic. It must never import from ``demo/``.

Contents:
    config      environment-driven configuration
    compat      pydantic compatibility layer
    errors      infrastructure error types
    budget      token / attempt budgets (infrastructure bounds only)
    records     append-only record model
    store       durable JSON state + JSONL append-only history
    llm         OpenRouter gateway with fallback models
    structured  structured-output parsing and schema repair
    runner      explicit state-machine execution
"""

__all__ = [
    "config",
    "compat",
    "errors",
    "budget",
    "records",
    "store",
    "llm",
    "structured",
    "runner",
]

__version__ = "0.1.0"
