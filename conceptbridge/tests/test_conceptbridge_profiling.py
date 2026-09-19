"""Profiling tests (covers spec TEST 1)."""

import csv
from pathlib import Path

from helpers import assert_raises

from demo.conceptbridge import profiling
from demo.conceptbridge.profiling import (CONCEPT_MAP_CSV, DATA_DIR, QUIZ_CSV,
                                          ProfilingError, build_profiles,
                                          load_concept_map, load_quiz)

EXPECTED = {}
with (DATA_DIR / "sample_students.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        sid = row.pop("student_id")
        row.pop("student_name")
        EXPECTED[sid] = {k: float(v) for k, v in row.items()}


def test_every_student_has_every_concept_in_range():
    profiles = profiling.profile_students(QUIZ_CSV, CONCEPT_MAP_CSV)
    concepts = set(load_concept_map(CONCEPT_MAP_CSV).values())
    assert len(profiles) == 6
    for item in profiles:
        assert set(item.as_dict()) == concepts
        for score in item.as_dict().values():
            assert 0.0 <= score <= 1.0


def test_known_scores_match_expected_values():
    profiles = {p.student_id: p for p in profiling.profile_students(QUIZ_CSV,
                                                                    CONCEPT_MAP_CSV)}
    for sid, expected in EXPECTED.items():
        for concept, value in expected.items():
            assert abs(profiles[sid].score_for(concept) - value) < 1e-6, (sid, concept)


def test_aggregation_is_a_plain_mean():
    rows = [
        {"student_id": "X", "student_name": "X", "question_id": "Q1",
         "score": 1.0, "response_text": ""},
        {"student_id": "X", "student_name": "X", "question_id": "Q2",
         "score": 0.0, "response_text": ""},
    ]
    built = build_profiles(rows, {"Q1": "Arrays", "Q2": "Arrays"})
    assert built[0].score_for("Arrays") == 0.5


def test_unmapped_question_is_rejected():
    rows = [{"student_id": "X", "student_name": "X", "question_id": "Q99",
             "score": 1.0, "response_text": ""}]
    assert_raises(ProfilingError, build_profiles, rows, {"Q1": "Arrays"})


def test_non_numeric_score_is_rejected():
    import tempfile
    path = Path(tempfile.mkdtemp()) / "bad.csv"
    path.write_text("student_id,student_name,question_id,score\n"
                    "S1,A,Q1,not-a-number\n", encoding="utf-8")
    assert_raises(ProfilingError, load_quiz, path)


def test_student_filter_selects_a_subset():
    profiles = profiling.profile_students(QUIZ_CSV, CONCEPT_MAP_CSV,
                                          students=["Ananya", "Priya"])
    assert sorted(p.student_name for p in profiles) == ["Ananya", "Priya"]
