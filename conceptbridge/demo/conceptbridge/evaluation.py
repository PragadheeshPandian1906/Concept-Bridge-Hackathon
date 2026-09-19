"""EVALUATION - deterministic learning gain.

    gain = after_score - before_score

A match is *effective* when BOTH directions clear
``LEARNING_GAIN_THRESHOLD`` on the concept the session focused on
(``matching.primary_concept``). Reciprocity is measured the same way it
is matched: one-sided learning is not success.

No model is ever asked to compute or judge a gain.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .matching import primary_concept
from .profiling import clamp
from .schema import (LearningOutcome, MatchCandidate, ProfileUpdate,
                     SessionOutcome, StudentProfile)

LEARNING_GAIN_THRESHOLD = 0.10

DATA_DIR = Path(__file__).resolve().parent / "data"
FOLLOWUP_CSV = DATA_DIR / "followup_quiz.csv"

#: Used only when the follow-up CSV has no rows for a pair (e.g. a match
#: produced by an interactive run). Documented and deterministic.
DEFAULT_GAIN = 0.40


def load_followup(path: str | Path = FOLLOWUP_CSV) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                score = float(row["score"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append({
                "scenario": (row.get("scenario") or "success").strip(),
                "match_key": (row.get("match_key") or "").strip(),
                "student_id": (row.get("student_id") or "").strip(),
                "question_id": (row.get("question_id") or "").strip(),
                "concept": (row.get("concept") or "").strip(),
                "score": clamp(score),
            })
    return rows


def followup_score(rows: list[dict], scenario: str, match_key: str,
                   student_id: str, concept: str) -> float | None:
    """Mean of the follow-up questions for one student+concept, or None."""
    for key in (scenario, "success"):
        hits = [r["score"] for r in rows
                if r["scenario"] == key and r["match_key"] == match_key
                and r["student_id"] == student_id and r["concept"] == concept]
        if hits:
            return clamp(round(sum(hits) / len(hits), 4))
    return None


def learning_gain(before: float, after: float) -> float:
    return round(after - before, 4)


def evaluate_match(candidate: MatchCandidate,
                   profile_a: StudentProfile,
                   profile_b: StudentProfile,
                   scenario: str = "success",
                   followup_rows: list[dict] | None = None,
                   threshold: float = LEARNING_GAIN_THRESHOLD) -> SessionOutcome:
    """Measure the follow-up quiz and decide whether the match worked."""
    rows = load_followup() if followup_rows is None else followup_rows
    outcomes: list[LearningOutcome] = []
    direction_ok: list[bool] = []

    # b learns from a, then a learns from b
    for teacher, learner, taught in (
        (profile_a, profile_b, candidate.a_teaches),
        (profile_b, profile_a, candidate.b_teaches),
    ):
        concept = primary_concept(teacher, learner, taught)
        if concept is None:
            direction_ok.append(False)
            continue
        before = learner.score_for(concept)
        after = followup_score(rows, scenario, candidate.match_id,
                               learner.student_id, concept)
        if after is None:
            after = clamp(before + DEFAULT_GAIN)
        gain = learning_gain(before, after)
        outcomes.append(LearningOutcome(
            student_id=learner.student_id,
            concept=concept,
            before_score=before,
            after_score=after,
            gain=gain,
        ))
        direction_ok.append(gain >= threshold)

    effective = bool(direction_ok) and all(direction_ok)
    return SessionOutcome(match_id=candidate.match_id, outcomes=outcomes,
                          effective=effective)


def build_profile_updates(outcome: SessionOutcome,
                          profiles: dict[str, StudentProfile]) -> list[ProfileUpdate]:
    """Profile deltas implied by an effective outcome (empty otherwise)."""
    if not outcome.effective:
        return []
    updates = []
    for item in outcome.outcomes:
        profile = profiles[item.student_id]
        old = profile.score_for(item.concept)
        updates.append(ProfileUpdate(
            student_id=item.student_id,
            concept=item.concept,
            old_score=old,
            new_score=clamp(item.after_score),
            gain=learning_gain(old, item.after_score),
        ))
    return updates


def apply_updates(profiles: dict[str, StudentProfile],
                  updates: list[ProfileUpdate]) -> dict[str, StudentProfile]:
    """Return a new profile map with updates applied (originals untouched)."""
    out = dict(profiles)
    for update in updates:
        out[update.student_id] = out[update.student_id].with_score(
            update.concept, update.new_score
        )
    return out
