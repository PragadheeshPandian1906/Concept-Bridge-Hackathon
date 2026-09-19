from demo.conceptbridge.matchmaking import agent as matchmaking
from demo.conceptbridge.matchmaking import graph as G
from demo.conceptbridge.orchestrator import run_matching, run_profiling
from demo.conceptbridge.state import RunState, load_state


def test_group_scoring_is_explainable(seeded):
    db, run_id = seeded
    run_profiling(db, run_id)
    G.build_graph(db)
    candidate = matchmaking.score_group(db, ["S001", "S002"])
    assert candidate is not None
    assert set(candidate.components) == {
        "coverage",
        "reciprocity",
        "transfer_strength",
        "fairness",
        "observed_effectiveness",
        "previous_match_penalty",
        "teaching_load_penalty",
    }
    assert candidate.properties.reciprocal_relationships >= 1


def test_group_size_bounds(seeded):
    db, run_id = seeded
    run_profiling(db, run_id)
    G.build_graph(db)
    for candidate in matchmaking.candidate_groups(db):
        assert 2 <= len(candidate.members) <= 5


def test_matching_proposes_and_sets_state(seeded):
    db, run_id = seeded
    run_profiling(db, run_id)
    result = run_matching(db, run_id)
    assert result["match"] is not None
    assert load_state(db, run_id) is RunState.WAITING_FOR_APPROVAL


def test_no_match_found_for_isolated_student(seeded):
    db, run_id = seeded
    run_profiling(db, run_id)
    result = run_matching(db, run_id, student_ids=["S008"])
    assert result["match"] is None
    assert load_state(db, run_id) is RunState.NO_MATCH_FOUND
