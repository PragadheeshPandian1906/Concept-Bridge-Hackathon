"""SESSION - the two places where a language model is actually useful.

1. explaining a match that Python already decided
2. writing the peer-learning session plan

Both go through ``slice.structured.complete_structured`` (typed output,
schema repair, budget, fallback models). Both have a deterministic
fallback, so a model outage degrades the wording, never the pipeline.

Nothing here computes a score, a gain, a threshold or a transition.
"""

from __future__ import annotations

from pathlib import Path

from slice.budget import Budget
from slice.config import Config
from slice.errors import SliceError
from slice.structured import complete_structured

from .matching import fallback_explanation, primary_concept
from .schema import MatchCandidate, MatchExplanation, SessionPlan, StudentProfile

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


# ------------------------------------------------------------- prompts
def load_prompt(name: str) -> tuple[str, str]:
    """Return ``(system, user_template)`` for a prompt file."""
    text = (PROMPT_DIR / name).read_text(encoding="utf-8")
    shared = (PROMPT_DIR / "_shared.md").read_text(encoding="utf-8")

    system, _, user = text.partition("\nUSER\n")
    _, _, system = system.partition("\nSYSTEM\n")
    system = (system.strip() or "You are a careful teaching assistant.")
    return f"{system}\n\n{shared.strip()}", user.strip()


def render(template: str, values: dict) -> str:
    """Literal ``{key}`` substitution (the templates contain JSON braces)."""
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", str(value))
    return out


def _score_block(profile: StudentProfile) -> str:
    return "\n".join(f"  {c.concept}: {c.score:.2f}" for c in profile.concepts)


# --------------------------------------------------- match explanation
def explain_match(candidate: MatchCandidate, a: StudentProfile, b: StudentProfile,
                  *, config: Config | None = None, budget: Budget | None = None,
                  provider=None, use_llm: bool = True,
                  on_event=None) -> tuple[str, str]:
    """Return ``(explanation_text, source)`` where source is llm|fallback."""
    if not use_llm:
        return fallback_explanation(candidate, a, b), "fallback"

    system, template = load_prompt("match_explain.md")
    prompt = render(template, {
        "match_id": candidate.match_id,
        "compatibility": f"{candidate.compatibility_score:.2f}",
        "a_name": a.student_name, "a_id": a.student_id, "a_scores": _score_block(a),
        "b_name": b.student_name, "b_id": b.student_id, "b_scores": _score_block(b),
        "a_teaches": ", ".join(candidate.a_teaches),
        "b_teaches": ", ".join(candidate.b_teaches),
        "a_to_b": f"{candidate.a_to_b_score:.2f}",
        "b_to_a": f"{candidate.b_to_a_score:.2f}",
        "balance": f"{candidate.balance:.2f}",
    })
    try:
        explanation = complete_structured(
            prompt, MatchExplanation, system=system, config=config,
            budget=budget, provider=provider, label="match_explain",
            on_event=on_event,
        )
    except SliceError as exc:
        if on_event:
            on_event({"event": "llm_degraded", "step": "match_explain", "error": str(exc)})
        return fallback_explanation(candidate, a, b), "fallback"

    text = "\n".join([
        explanation.summary,
        f"- {a.student_name} -> {b.student_name}: {explanation.a_teaches_reason}",
        f"- {b.student_name} -> {a.student_name}: {explanation.b_teaches_reason}",
    ])
    return text, "llm"


# ---------------------------------------------------------- session plan
def deterministic_session(candidate: MatchCandidate, a: StudentProfile,
                          b: StudentProfile) -> SessionPlan:
    """Template session built only from matcher output. No model needed."""
    a_primary = primary_concept(a, b, candidate.a_teaches) or "-"
    b_primary = primary_concept(b, a, candidate.b_teaches) or "-"

    objectives = [f"{b.student_name} can explain the core idea of {c}."
                  for c in candidate.a_teaches]
    objectives += [f"{a.student_name} can explain the core idea of {c}."
                   for c in candidate.b_teaches]

    directions = [f"{a.student_name} -> {b.student_name}: {', '.join(candidate.a_teaches)}",
                  f"{b.student_name} -> {a.student_name}: {', '.join(candidate.b_teaches)}"]

    prompts = [
        f"{a.student_name}: explain {a_primary} with one worked example.",
        f"{b.student_name}: explain {b_primary} with one worked example.",
        f"Each of you sets the other one short problem on the concept you taught.",
    ]

    return SessionPlan(
        match_id=candidate.match_id,
        learning_objectives=objectives[:4],
        teaching_directions=directions,
        teaching_prompts=prompts,
        shared_challenge=(f"Together, solve one problem that combines {a_primary} "
                          f"and {b_primary}, and write down the two steps that were hardest."),
        follow_up_questions=[
            f"One question on {a_primary} for {b.student_name}.",
            f"One question on {b_primary} for {a.student_name}.",
            "One question that mixes both concepts.",
        ],
    )


def generate_session(candidate: MatchCandidate, a: StudentProfile, b: StudentProfile,
                     *, config: Config | None = None, budget: Budget | None = None,
                     provider=None, use_llm: bool = True,
                     on_event=None) -> tuple[SessionPlan, str]:
    """Return ``(plan, source)`` where source is llm|fallback."""
    if not use_llm:
        return deterministic_session(candidate, a, b), "fallback"

    system, template = load_prompt("session.md")
    prompt = render(template, {
        "match_id": candidate.match_id,
        "a_name": a.student_name, "b_name": b.student_name,
        "a_teaches": ", ".join(candidate.a_teaches),
        "b_teaches": ", ".join(candidate.b_teaches),
        "a_primary": primary_concept(a, b, candidate.a_teaches) or "-",
        "b_primary": primary_concept(b, a, candidate.b_teaches) or "-",
    })
    try:
        plan = complete_structured(
            prompt, SessionPlan, system=system, config=config, budget=budget,
            provider=provider, label="session", on_event=on_event,
        )
    except SliceError as exc:
        if on_event:
            on_event({"event": "llm_degraded", "step": "session", "error": str(exc)})
        return deterministic_session(candidate, a, b), "fallback"

    # The model may not echo the match id correctly; the deterministic id wins.
    if plan.match_id != candidate.match_id:
        plan = plan.model_copy(update={"match_id": candidate.match_id})
    return plan, "llm"
