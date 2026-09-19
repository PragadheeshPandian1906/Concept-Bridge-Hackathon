"""Deterministic scoring. MCQs never touch the LLM."""
from __future__ import annotations


def score_mcq(student_answer: str | None, correct_answer: str | None) -> float:
    if student_answer is None or correct_answer is None:
        return 0.0
    return 1.0 if student_answer.strip().lower() == correct_answer.strip().lower() else 0.0


def normalize(score: float, max_marks: float) -> float:
    if max_marks <= 0:
        return 0.0
    return max(0.0, min(1.0, score / max_marks))


def aggregate_by_concept(rows: list[tuple[str, float]]) -> dict[str, float]:
    """rows = [(concept_id, normalized_score), ...] -> mean per concept, clipped to [0,1]."""
    totals: dict[str, list[float]] = {}
    for concept_id, value in rows:
        totals.setdefault(concept_id, []).append(value)
    return {cid: round(max(0.0, min(1.0, sum(v) / len(v))), 4) for cid, v in totals.items()}
