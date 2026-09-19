from pathlib import Path

from demo.conceptbridge.flow import ConceptBridgeFlow, JsonState
from demo.conceptbridge.schema import State
from demo.conceptbridge.stub import StubModel

DATA = Path("demo/conceptbridge/data")


def make_flow(tmp_path):
    return ConceptBridgeFlow(JsonState(tmp_path / "state.json", tmp_path / "records.jsonl"), call=StubModel())


def test_approval_paths_and_success(tmp_path):
    flow = make_flow(tmp_path)
    state = flow.start(DATA / "quiz.csv", DATA / "question_concepts.csv")
    assert state["state"] == State.WAITING_FOR_APPROVAL.value
    state = flow.advance(False)
    assert state["state"] == State.MATCHING.value
    state = flow.advance(True)
    assert state["state"] == State.FINISHED.value
    assert state["profile_updates"]


def test_ineffective_match_rematches(tmp_path):
    flow = make_flow(tmp_path)
    flow.start(DATA / "quiz.csv", DATA / "question_concepts.csv")
    state = flow.advance(True, "ineffective")
    assert state["state"] == State.FINISHED.value
    assert len(state["outcomes"]) == 2
    assert len(set(state["excluded_matches"])) == 1


def test_persistence_and_adversarial_text(tmp_path):
    flow = make_flow(tmp_path)
    state = flow.start(DATA / "quiz.csv", DATA / "question_concepts.csv")
    original = state["profiles"]["ananya"]["concepts"]
    assert all(item["score"] <= 1 for item in original)
    restored = JsonState(tmp_path / "state.json", tmp_path / "records.jsonl").load()
    assert restored["state"] == State.WAITING_FOR_APPROVAL.value
    assert restored["profiles"]["ananya"] == state["profiles"]["ananya"]


def test_interactive_scores_are_used_for_evaluation(tmp_path):
    flow = make_flow(tmp_path)
    state = flow.start(DATA / "quiz.csv", DATA / "question_concepts.csv",
                       followup_quiz=DATA / "followup_quiz.csv")
    state = flow.advance(True, pause_after_session=True)
    assert state["state"] == State.EVALUATION.value
    candidate = state["candidate"]
    observations = []
    for student_id, concepts in ((candidate["student_a"], candidate["b_teaches"]),
                                 (candidate["student_b"], candidate["a_teaches"])):
        scores = {item["concept"]: item["score"] for item in state["profiles"][student_id]["concepts"]}
        observations.extend((student_id, concept, scores[concept], scores[concept] + .2)
                            for concept in concepts)
    state = flow.advance(observations=observations)
    assert state["outcomes"][-1]["outcomes"][0]["after_score"] == .62
    assert state["state"] == State.FINISHED.value