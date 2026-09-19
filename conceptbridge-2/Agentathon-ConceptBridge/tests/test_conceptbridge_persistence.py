import json
from pathlib import Path

from demo.conceptbridge.flow import ConceptBridgeFlow, JsonState
from demo.conceptbridge.stub import StubModel


def test_records_are_append_only_jsonl(tmp_path):
    data = Path("demo/conceptbridge/data")
    store = JsonState(tmp_path / "state.json", tmp_path / "records.jsonl")
    flow = ConceptBridgeFlow(store, call=StubModel())
    flow.start(data / "quiz.csv", data / "question_concepts.csv")
    records = [json.loads(line) for line in (tmp_path / "records.jsonl").read_text().splitlines()]
    assert records
    assert {record["kind"] for record in records} >= {"input", "student_profile", "state_transition", "match_candidate"}