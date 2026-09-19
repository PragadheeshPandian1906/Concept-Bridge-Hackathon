from __future__ import annotations

import json
from typing import Any, Type
from pydantic import BaseModel

from .schema import MatchCandidate, SessionPlan


class StubModel:
    """Deterministic provider used by the exact same flow as live mode."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, *, settings: Any, budget: Any, messages: list[dict],
                 schema: Type[BaseModel] | None = None, model: str | None = None,
                 step: str = "call", timeout: float = 120.0) -> Any:
        self.calls.append(step)
        budget.record_tokens(1)
        if schema is SessionPlan:
            return SessionPlan(match_id=json.loads(messages[-1]["content"])["match_id"],
                learning_objectives=["Explain the reciprocal concepts using examples."],
                teaching_directions=["Teach from the stronger student's evidence-backed concepts."],
                teaching_prompts=["Explain the idea simply.", "Ask the learner to identify the key step.", "Give one practice problem."],
                shared_challenge="Solve one targeted problem from each teaching direction.",
                follow_up_questions=["What is the main idea?", "Which step is easiest to confuse?", "Solve a small example."])
        return schema.model_validate({}) if schema else ""