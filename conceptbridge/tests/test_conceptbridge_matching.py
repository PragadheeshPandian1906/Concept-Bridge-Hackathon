"""Reciprocal matching tests (covers spec TEST 2, TEST 3)."""

from helpers import profile

from demo.conceptbridge import matching
from demo.conceptbridge.matching import (generate_candidates, match_id_for,
                                         primary_concept, score_pair,
                                         teachable_concepts)


def pair_ab():
    a = profile("A", "Alice", Recursion=0.90, SQL=0.30)
    b = profile("B", "Bob", Recursion=0.40, SQL=0.90)
    return a, b


def test_reciprocal_pair_is_eligible():
    """TEST 2 - each direction teaches, score is positive."""
    a, b = pair_ab()
    candidate = score_pair(a, b)
    assert candidate is not None
    assert candidate.a_teaches == ["Recursion"]
    assert candidate.b_teaches == ["SQL"]
    assert candidate.compatibility_score > 0
    assert candidate.a_to_b_score > 0 and candidate.b_to_a_score > 0
    assert candidate.match_id == "A|B"


def test_two_strong_students_are_not_a_match():
    """TEST 3 - strength alone is not compatibility."""
    a = profile("A", "Alice", Recursion=0.95, SQL=0.92)
    b = profile("B", "Bob", Recursion=0.91, SQL=0.90)
    assert score_pair(a, b) is None
    assert generate_candidates([a, b]).items == []


def test_one_way_tutoring_is_not_a_match():
    a = profile("A", "Alice", Recursion=0.95, SQL=0.92)
    b = profile("B", "Bob", Recursion=0.20, SQL=0.25)
    assert score_pair(a, b) is None


def test_threshold_boundaries_are_respected():
    a = profile("A", "Alice", Recursion=0.70, SQL=0.10)
    b = profile("B", "Bob", Recursion=0.60, SQL=0.70)
    # b's 0.60 is NOT below the gap threshold, so A cannot teach Recursion
    assert teachable_concepts(a, b) == []
    assert score_pair(a, b) is None


def test_ordering_is_deterministic_and_descending():
    a = profile("A", "Alice", Recursion=0.90, SQL=0.30)
    b = profile("B", "Bob", Recursion=0.40, SQL=0.90)
    c = profile("C", "Cara", Recursion=0.55, SQL=0.75)
    items = generate_candidates([a, b, c]).items
    scores = [i.compatibility_score for i in items]
    assert scores == sorted(scores, reverse=True)
    assert generate_candidates([c, b, a]).items == items  # input order irrelevant


def test_excluded_pairs_are_never_returned():
    a, b = pair_ab()
    c = profile("C", "Cara", Recursion=0.50, SQL=0.80)
    assert any(i.match_id == "A|B" for i in generate_candidates([a, b, c]).items)
    remaining = generate_candidates([a, b, c], excluded=["A|B"]).items
    assert all(i.match_id != "A|B" for i in remaining)


def test_primary_concept_is_the_largest_gap():
    a = profile("A", "Alice", Recursion=0.90, Arrays=0.80)
    b = profile("B", "Bob", Recursion=0.30, Arrays=0.55)
    assert primary_concept(a, b, ["Recursion", "Arrays"]) == "Recursion"


def test_match_id_is_order_independent():
    assert match_id_for("S2", "S1") == match_id_for("S1", "S2") == "S1|S2"


def test_pilot_dataset_top_candidate_is_ananya_rahul():
    from demo.conceptbridge.profiling import profile_students
    items = generate_candidates(profile_students()).items
    assert items[0].match_id == "S1|S2"
    assert items[1].match_id == "S1|S3"
    # Arjun is strong everywhere with no gaps: he can never form a pair
    assert all("S6" not in i.match_id for i in items)


def test_fallback_explanation_only_mentions_given_concepts():
    a, b = pair_ab()
    candidate = score_pair(a, b)
    text = matching.fallback_explanation(candidate, a, b)
    assert "Recursion" in text and "SQL" in text
    assert "mastery" not in text.lower()
