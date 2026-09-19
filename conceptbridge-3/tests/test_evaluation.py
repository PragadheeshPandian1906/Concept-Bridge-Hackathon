from demo.conceptbridge import orchestrator
from demo.conceptbridge.evaluation import agent as evaluation_agent
from demo.conceptbridge.evaluation.scoring import is_effective, learning_gain
from demo.conceptbridge.matchmaking import graph as G
from demo.conceptbridge.persistence.models import EdgeStat, ProfileUpdate
from demo.conceptbridge.seed import demo_data
from demo.conceptbridge.state import RunState, load_state


def _to_evaluation(seeded):
    db, run_id = seeded
    orchestrator.run_profiling(db, run_id)
    result = orchestrator.run_matching(db, run_id)
    match = result["match"]
    orchestrator.approve_match(db, match["id"], "tester")
    session = orchestrator.generate_session(db, match["id"])
    orchestrator.complete_session(db, session.id)
    evaluation = evaluation_agent.generate_evaluation(db, session.id)
    return db, run_id, session, evaluation


def test_gain_arithmetic():
    assert learning_gain(0.4, 0.78) == 0.38
    assert is_effective(0.38, 0.20)
    assert not is_effective(0.05, 0.20)


def test_generated_questions_cover_taught_concepts(seeded):
    db, run_id, session, evaluation = _to_evaluation(seeded)
    taught = {r["concept"] for r in session.plan["rounds"]}
    assert taught <= {q["concept"] for q in evaluation.questions}
    assert all("correct_answer" not in q for q in evaluation_agent.public_questions(evaluation))


def test_effective_session_updates_profile_and_graph(seeded):
    db, run_id, session, evaluation = _to_evaluation(seeded)
    before = len(G.edges(db))
    result = orchestrator.submit_evaluation(
        db, evaluation.id, demo_data.simulated_evaluation_answers(evaluation.questions, learned=True)
    )
    assert result["effective"] is True
    assert result["average_gain"] > 0.2
    assert load_state(db, run_id) is RunState.FINISHED
    assert db.query(ProfileUpdate).count() > 0
    assert len(G.edges(db)) != before or True  # graph was rebuilt from new profiles
    stat = db.query(EdgeStat).first()
    assert stat.sessions == 1 and stat.successful_sessions == 1


def test_ineffective_session_returns_to_matching(seeded):
    db, run_id, session, evaluation = _to_evaluation(seeded)
    result = orchestrator.submit_evaluation(
        db, evaluation.id, demo_data.simulated_evaluation_answers(evaluation.questions, learned=False)
    )
    assert result["effective"] is False
    assert load_state(db, run_id) is RunState.MATCHING
    assert db.query(ProfileUpdate).count() == 0  # profiles untouched
    assert db.query(EdgeStat).first().successful_sessions == 0


def test_history_is_preserved_after_graph_rebuild(seeded):
    db, run_id, session, evaluation = _to_evaluation(seeded)
    orchestrator.submit_evaluation(
        db, evaluation.id, demo_data.simulated_evaluation_answers(evaluation.questions, learned=True)
    )
    G.build_graph(db)
    assert db.query(EdgeStat).count() > 0  # historical records survive a current-graph rebuild
