from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .schema import MatchCandidate, SessionPlan

_PROMPTS = Path(__file__).parent / "prompts"


def _prompt(name: str) -> str:
    return (_PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def generate_session(candidate: MatchCandidate, call: Callable[..., Any], settings: Any, budget: Any) -> SessionPlan:
    messages = [{"role": "system", "content": _prompt("session")},
                {"role": "user", "content": json.dumps(candidate.model_dump())}]
    try:
        plan = call(settings=settings, budget=budget, messages=messages, schema=SessionPlan, step="session")
        if plan.match_id != candidate.match_id:
            plan.match_id = candidate.match_id
        return plan
    except Exception:
        return SessionPlan(match_id=candidate.match_id,
                           learning_objectives=[f"Learn {', '.join(candidate.a_teaches + candidate.b_teaches)}."],
                           teaching_directions=[f"{candidate.student_a} teaches {', '.join(candidate.a_teaches)}.", f"{candidate.student_b} teaches {', '.join(candidate.b_teaches)}."],
                           teaching_prompts=["Explain one concept with an example.", "Ask the learner to solve a small example.", "Check the learner's reasoning."],
                           shared_challenge="Solve one problem combining both teaching directions.",
                           follow_up_questions=["Define the idea.", "Work through an example.", "Explain the tricky step."])