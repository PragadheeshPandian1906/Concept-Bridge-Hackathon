from demo.conceptbridge.schema import ConceptScore, StudentProfile, State


def test_schema_is_strictly_serializable():
    profile = StudentProfile(student_id="a", student_name="A", concepts=[ConceptScore(concept="Arrays", score=.5)])
    assert profile.model_dump()["concepts"][0]["score"] == .5
    assert State.MATCHING.value == "MATCHING"