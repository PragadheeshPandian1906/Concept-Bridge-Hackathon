"""Deterministic replacement for the open-ended grader in DEMO_MODE."""
from __future__ import annotations

import hashlib


def stub_open_ended(question_text: str, model_answer: str, student_answer: str, max_marks: int = 5) -> dict:
    student = (student_answer or "").lower()
    keywords = [w for w in (model_answer or "").lower().replace(",", " ").split() if len(w) > 4]
    hits = sum(1 for w in set(keywords) if w in student)
    coverage = hits / max(1, len(set(keywords)))
    length_factor = min(1.0, len(student.split()) / 40)
    raw = 0.75 * coverage + 0.25 * length_factor
    # tiny deterministic jitter so students differ even with similar answers
    jitter = int(hashlib.md5((question_text + student).encode()).hexdigest(), 16) % 7 / 100
    normalized = max(0.0, min(1.0, round(raw + jitter, 3)))
    missing = [w for w in set(keywords) if w not in student][:3]
    return {
        "score": round(normalized * max_marks, 2),
        "normalized_score": normalized,
        "strengths": [f"mentions '{w}'" for w in list(set(keywords))[:2] if w in student],
        "missing_points": missing,
        "misconceptions": [],
    }
