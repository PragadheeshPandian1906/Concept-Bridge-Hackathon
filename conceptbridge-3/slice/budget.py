"""Infrastructure budget. This is NOT the domain revision limit."""
from __future__ import annotations

from dataclasses import dataclass, field


class CapExhausted(RuntimeError):
    pass


@dataclass
class Budget:
    max_calls: int = 40
    max_tokens: int = 200_000
    calls: int = 0
    tokens: int = 0
    by_step: dict = field(default_factory=dict)

    def check(self, step: str) -> None:
        if self.calls >= self.max_calls:
            raise CapExhausted(f"call cap reached ({self.max_calls}) at step={step}")
        if self.tokens >= self.max_tokens:
            raise CapExhausted(f"token cap reached ({self.max_tokens}) at step={step}")

    def record(self, step: str, tokens: int) -> None:
        self.calls += 1
        self.tokens += tokens
        entry = self.by_step.setdefault(step, {"calls": 0, "tokens": 0})
        entry["calls"] += 1
        entry["tokens"] += tokens

    def snapshot(self) -> dict:
        return {"calls": self.calls, "tokens": self.tokens, "by_step": dict(self.by_step)}
