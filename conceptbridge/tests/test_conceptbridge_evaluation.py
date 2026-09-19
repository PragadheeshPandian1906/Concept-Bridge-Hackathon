"""Learning-gain tests (covers spec TEST 6, TEST 7)."""

from helpers import profile

from demo.conceptbridge import evaluation
from demo.conceptbridge.evaluation import (LEARNING_GAIN_THRESHOLD,
                                           apply_updates, build_profile_updates,
                                           evaluate_match, learning_gain)
from demo.conceptbridge.matching import score_pair


def setup_pair():
    a = profile("S1", "Ananya", Recursion=0.90, SQL=0.35)
    b = profile("S2", "Rahul", Recursion=0.40, SQL=0.92)
    return a, b, score_pair(a, b)


def followup(after_a, after_b):
    return [
        {"scenario": "t", "match_key": "S1|S2", "student_id": "S1",
         "question_id": "FQ1", "concept": "SQL", "score": after_a},
        {"scenario": "t", "match_key": "S1|S2", "student_id": "S2",
         "question_id": "FQ1", "concept": "Recursion", "score": after_b},
    ]


def test_gain_is_a_subtraction():
    assert learning_gain(0.35, 0.75) == 0.40
    assert learning_gain(0.35, 0.38) == 0.03


def test_effective_outcome():
    """TEST 6 - 0.35 -> 0.75 is a gain of 0.40 and is effective."""
    a, b, candidate = setup_pair()
    outcome = evaluate_match(candidate, a, b, scenario="t",
                             followup_rows=followup(0.75, 0.80))
    assert outcome.effective is True
    by_student = {o.student_id: o for o in outcome.outcomes}
    assert by_student["S1"].concept == "SQL"
    assert by_student["S1"].before_score == 0.35
    assert by_student["S1"].after_score == 0.75
    assert by_student["S1"].gain == 0.40


def test_ineffective_outcome():
    """TEST 7 - 0.35 -> 0.38 is a gain of 0.03 and is not effective."""
    a, b, candidate = setup_pair()
    outcome = evaluate_match(candidate, a, b, scenario="t",
                             followup_rows=followup(0.38, 0.42))
    assert outcome.effective is False
    assert {o.gain for o in outcome.outcomes} == {0.03, 0.02}
    assert build_profile_updates(outcome, {"S1": a, "S2": b}) == []


def test_one_sided_learning_is_not_effective():
    a, b, candidate = setup_pair()
    outcome = evaluate_match(candidate, a, b, scenario="t",
                             followup_rows=followup(0.90, 0.41))
    assert outcome.effective is False


def test_threshold_boundary_counts_as_effective():
    a, b, candidate = setup_pair()
    outcome = evaluate_match(
        candidate, a, b, scenario="t",
        followup_rows=followup(0.35 + LEARNING_GAIN_THRESHOLD,
                               0.40 + LEARNING_GAIN_THRESHOLD))
    assert outcome.effective is True


def test_profile_update_applies_only_the_taught_concept():
    a, b, candidate = setup_pair()
    outcome = evaluate_match(candidate, a, b, scenario="t",
                             followup_rows=followup(0.75, 0.80))
    profiles = {"S1": a, "S2": b}
    updates = build_profile_updates(outcome, profiles)
    updated = apply_updates(profiles, updates)

    assert updated["S1"].score_for("SQL") == 0.75
    assert updated["S1"].score_for("Recursion") == 0.90   # untouched
    assert updated["S2"].score_for("Recursion") == 0.80
    assert profiles["S1"].score_for("SQL") == 0.35        # original preserved


def test_missing_followup_rows_fall_back_deterministically():
    a, b, candidate = setup_pair()
    outcome = evaluate_match(candidate, a, b, scenario="unknown", followup_rows=[])
    assert all(o.gain == evaluation.DEFAULT_GAIN for o in outcome.outcomes)
