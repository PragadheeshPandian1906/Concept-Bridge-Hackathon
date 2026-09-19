import pytest
from fastapi.testclient import TestClient

from demo.conceptbridge.api.main import app
from demo.conceptbridge.persistence.database import SessionLocal, reset_db
from demo.conceptbridge.seed import demo_data


@pytest.fixture()
def client():
    reset_db()
    session = SessionLocal()
    demo_data.seed(session)
    session.close()
    return TestClient(app)


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True  # runs without an API key


def test_full_lifecycle_over_http(client):
    answers = demo_data.quiz_answers("api")
    submitted = client.post("/api/v1/quiz/submit", json={"answers": answers})
    assert submitted.status_code == 200
    run_id = submitted.json()["run_id"]

    assert client.post("/api/v1/profiling/run", json={"run_id": run_id}).status_code == 200
    profile = client.get("/api/v1/students/S001/profile").json()
    assert profile["concept_scores"]["C_REC"] > 0.8

    matching = client.post("/api/v1/matching/run", json={"run_id": run_id}).json()
    match_id = matching["match"]["id"]
    assert client.get("/api/v1/graph/health").json()["active_edge_count"] > 0

    client.post(f"/api/v1/matching/{match_id}/approve", json={"decided_by": "pytest"})
    session = client.post("/api/v1/sessions/generate", json={"match_id": match_id}).json()
    client.post(f"/api/v1/sessions/{session['id']}/start")
    client.post(f"/api/v1/sessions/{session['id']}/complete")

    evaluation = client.post(f"/api/v1/evaluations/{session['id']}/generate").json()
    db = SessionLocal()
    from demo.conceptbridge.persistence.models import Evaluation

    full = db.get(Evaluation, evaluation["id"])
    payload = demo_data.simulated_evaluation_answers(full.questions, learned=True)
    db.close()

    result = client.post(f"/api/v1/evaluations/{evaluation['id']}/submit", json={"answers": payload}).json()
    assert result["effective"] is True
    assert client.get(f"/api/v1/runs/{run_id}").json()["current_state"] == "FINISHED"
    assert len(client.get(f"/api/v1/runs/{run_id}/history").json()) >= 7
    assert client.get("/api/v1/analytics/overview").json()["students"] == 8


def test_unknown_ids_return_404(client):
    assert client.get("/api/v1/students/NOPE").status_code == 404
    assert client.get("/api/v1/runs/NOPE").status_code == 404
    assert client.post("/api/v1/sessions/generate", json={"match_id": "NOPE"}).status_code == 404
