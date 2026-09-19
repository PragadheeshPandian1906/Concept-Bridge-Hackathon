from demo.conceptbridge.orchestrator import run_profiling
from demo.conceptbridge.profiling.scoring import aggregate_by_concept, normalize, score_mcq
from demo.conceptbridge.profiling.stub import stub_open_ended


def test_mcq_scoring_is_deterministic():
    assert score_mcq("A", "A") == 1.0
    assert score_mcq("a", "A") == 1.0
    assert score_mcq("B", "A") == 0.0
    assert score_mcq(None, "A") == 0.0


def test_normalize_and_aggregate():
    assert normalize(4, 5) == 0.8
    assert normalize(9, 5) == 1.0
    assert aggregate_by_concept([("C1", 1.0), ("C1", 0.0), ("C2", 0.5)]) == {"C1": 0.5, "C2": 0.5}


def test_open_ended_stub_rewards_coverage():
    rubric = "basecase recursive stack termination"
    strong = stub_open_ended("q", rubric, "the basecase stops the recursive stack before termination " * 4)
    weak = stub_open_ended("q", rubric, "it repeats")
    assert strong["normalized_score"] > weak["normalized_score"]
    assert 0.0 <= weak["normalized_score"] <= 1.0


def test_profiling_builds_concept_vectors(seeded):
    db, run_id = seeded
    result = run_profiling(db, run_id)
    assert result["students_profiled"] == 8
    assert result["llm_calls"] > 0  # open-ended answers went through the LLM path (stubbed)
    s001 = result["profiles"]["S001"]
    assert s001["C_REC"] >= 0.9  # strong
    assert s001["C_SQL"] < 0.6  # gap
    assert all(0.0 <= v <= 1.0 for v in s001.values())
