"""Deterministic session content for DEMO_MODE."""
from __future__ import annotations


def stub_session(relationships: list[dict]) -> dict:
    rounds = []
    for rel in relationships:
        concept = rel["concept"]
        rounds.append(
            {
                "teacher": rel["teacher"],
                "learner": rel["learner"],
                "concept": concept,
                "objective": f"{rel['learner']} can explain and apply {concept} without help.",
                "explanation": (
                    f"{rel['teacher']} walks through {concept} from first principles: the definition, "
                    f"why it exists, and the one rule most people get wrong."
                ),
                "example": f"A worked example of {concept}, solved out loud step by step.",
                "activity": f"{rel['learner']} solves a fresh {concept} problem while {rel['teacher']} only asks questions.",
                "understanding_check": f"Ask {rel['learner']} to state, in their own words, when {concept} fails or does not apply.",
            }
        )
    concepts = ", ".join(sorted({r["concept"] for r in relationships}))
    return {"objective": f"Close the group's gaps in {concepts} through directed peer teaching.", "rounds": rounds}
