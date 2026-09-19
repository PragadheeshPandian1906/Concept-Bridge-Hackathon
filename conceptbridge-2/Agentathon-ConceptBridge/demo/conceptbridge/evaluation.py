from __future__ import annotations

from .schema import LearningOutcome, SessionOutcome

LEARNING_GAIN_THRESHOLD = 0.10


def evaluate_outcome(match_id: str, observations: list[tuple[str, str, float, float]]) -> SessionOutcome:
    outcomes = [LearningOutcome(student_id=sid, concept=concept,
                                before_score=before, after_score=after,
                                gain=round(after - before, 6))
                for sid, concept, before, after in observations]
    return SessionOutcome(match_id=match_id, outcomes=outcomes,
                          effective=bool(outcomes) and all(o.gain >= LEARNING_GAIN_THRESHOLD for o in outcomes))