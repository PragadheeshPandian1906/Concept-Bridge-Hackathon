from pathlib import Path

from demo.conceptbridge.profiling import build_profiles

DATA = Path("demo/conceptbridge/data")


def test_profiles_derive_from_question_evidence():
    profiles = build_profiles(DATA / "quiz.csv", DATA / "question_concepts.csv")
    ananya = next(p for p in profiles if p.student_id == "ananya")
    scores = {item.concept: item.score for item in ananya.concepts}
    assert scores["Arrays"] == .85
    assert scores["SQL Joins"] == .35
    assert len(scores) == 6
    assert all(0 <= score <= 1 for score in scores.values())