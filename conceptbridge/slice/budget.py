"""Infrastructure budgets.

IMPORTANT ARCHITECTURAL RULE
----------------------------
These counters bound *infrastructure* work: how many tokens a run may
spend and how many model attempts it may make.

They are NOT domain counters. A domain revision limit (e.g. "at most two
re-matching attempts") lives in the domain flow, never here. Never use a
token budget as a revision counter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import BudgetExceeded


@dataclass
class Budget:
    """Tracks tokens and attempts for a single run."""

    max_tokens: int = 20000
    max_attempts: int = 8
    used_tokens: int = 0
    used_attempts: int = 0
    calls: list = field(default_factory=list)

    # -- attempts ---------------------------------------------------
    def start_attempt(self, label: str = "llm") -> None:
        if self.used_attempts >= self.max_attempts:
            raise BudgetExceeded(
                f"attempt budget exhausted ({self.used_attempts}/{self.max_attempts})"
            )
        self.used_attempts += 1
        self.calls.append({"label": label, "attempt": self.used_attempts})

    # -- tokens -----------------------------------------------------
    def charge(self, tokens: int) -> None:
        self.used_tokens += max(0, int(tokens or 0))
        if self.used_tokens > self.max_tokens:
            raise BudgetExceeded(
                f"token budget exhausted ({self.used_tokens}/{self.max_tokens})"
            )

    def can_afford_attempt(self) -> bool:
        return self.used_attempts < self.max_attempts and self.used_tokens < self.max_tokens

    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    def snapshot(self) -> dict:
        return {
            "used_tokens": self.used_tokens,
            "max_tokens": self.max_tokens,
            "used_attempts": self.used_attempts,
            "max_attempts": self.max_attempts,
        }

    @classmethod
    def from_config(cls, config) -> "Budget":
        return cls(max_tokens=config.token_budget, max_attempts=config.max_attempts)
