"""The orchestrator is infrastructure, not an agent. It owns 'what happens next'."""
from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from slice.budget import Budget

from . import artifacts
from .evaluation import agent as evaluation_agent
from .matchmaking import agent as matchmaking_agent
from .matchmaking import graph as G
from .peer_learning import agent as peer_agent
from .persistence.models import MatchCandidate, Session
from .profiling import agent as profiling_agent
from .state import RunState, transition


def run_profiling(db: DBSession, run_id: str, budget: Budget | None = None) -> dict:
    result = profiling_agent.run_profiling(db, run_id, budget)
    transition(db, run_id, RunState.PROFILING, "quiz answers scored")
    artifacts.save(run_id, "profile_snapshot", result["profiles"])
    transition(db, run_id, RunState.MATCHING, "profiles ready")
    return result


def run_matching(db: DBSession, run_id: str, student_ids: list[str] | None = None) -> dict:
    G.build_graph(db)
    artifacts.save(run_id, "graph_snapshot_before", G.snapshot(db))
    match = matchmaking_agent.propose_match(db, run_id, student_ids)
    if match is None:
        transition(db, run_id, RunState.NO_MATCH_FOUND, "no eligible complementary group")
        return {"state": RunState.NO_MATCH_FOUND.value, "match": None, "health": G.graph_health(db)}
    transition(db, run_id, RunState.WAITING_FOR_APPROVAL, f"proposed {match.id}")
    artifacts.save(run_id, "match", _match_dict(match))
    return {"state": RunState.WAITING_FOR_APPROVAL.value, "match": _match_dict(match), "health": G.graph_health(db)}


def approve_match(db: DBSession, match_id: str, decided_by: str = "instructor", reason: str = "") -> dict:
    match = db.get(MatchCandidate, match_id)
    match.status = "APPROVED"
    match.decided_by = decided_by
    match.reason = reason
    db.commit()
    transition(db, match.run_id, RunState.SESSION, f"{match_id} approved by {decided_by}")
    return _match_dict(match)


def reject_match(db: DBSession, match_id: str, decided_by: str = "instructor", reason: str = "") -> dict:
    match = db.get(MatchCandidate, match_id)
    match.status = "REJECTED"
    match.decided_by = decided_by
    match.reason = reason
    db.commit()
    transition(db, match.run_id, RunState.MATCHING, f"{match_id} rejected: {reason}")
    return _match_dict(match)


def generate_session(db: DBSession, match_id: str, budget: Budget | None = None) -> Session:
    session = peer_agent.generate_session(db, match_id, budget)
    artifacts.save(session.run_id, "session_plan", session.plan)
    return session


def complete_session(db: DBSession, session_id: str) -> Session:
    session = peer_agent.complete_session(db, session_id)
    transition(db, session.run_id, RunState.EVALUATION, f"{session_id} completed")
    return session


def submit_evaluation(db: DBSession, evaluation_id: str, answers: list[dict], budget: Budget | None = None) -> dict:
    from .persistence.models import Evaluation

    evaluation = db.get(Evaluation, evaluation_id)
    result = evaluation_agent.submit_evaluation(db, evaluation_id, answers, budget)
    run_id = evaluation.run_id

    if result["effective"]:
        updates = evaluation_agent.apply_profile_updates(db, evaluation.session_id)
        transition(db, run_id, RunState.UPDATED_PROFILE, f"average gain {result['average_gain']}")
        G.build_graph(db)  # dynamic graph update
        artifacts.save(run_id, "graph_snapshot_after", G.snapshot(db))
        artifacts.save(run_id, "learning_gains", result)
        transition(db, run_id, RunState.FINISHED, "profile and graph updated")
        result["profile_updates"] = updates
        result["next_state"] = RunState.FINISHED.value
    else:
        transition(db, run_id, RunState.MATCHING, f"ineffective session (gain {result['average_gain']}) - rematching")
        artifacts.save(run_id, "learning_gains", result)
        result["profile_updates"] = []
        result["next_state"] = RunState.MATCHING.value
    return result


def finish_no_match(db: DBSession, run_id: str) -> None:
    transition(db, run_id, RunState.FINISHED, "no match available")


def _match_dict(match: MatchCandidate) -> dict:
    return {
        "id": match.id,
        "run_id": match.run_id,
        "members": match.members,
        "relationships": match.relationships,
        "properties": match.properties,
        "components": match.components,
        "score": match.score,
        "status": match.status,
        "decided_by": match.decided_by,
        "reason": match.reason,
    }
