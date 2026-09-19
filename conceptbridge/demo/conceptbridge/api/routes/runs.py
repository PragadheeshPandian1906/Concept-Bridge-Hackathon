from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ...matchmaking import graph as G
from ...persistence.database import get_db
from ...persistence.models import (
    Concept,
    Evaluation,
    LearningGain,
    MatchCandidate,
    Session,
    Student,
)
from ...state import RunState, create_run, get_run, history

router = APIRouter(tags=["runs"])


@router.post("/runs")
def new_run(db: DBSession = Depends(get_db)):
    run = create_run(db)
    return {"run_id": run.run_id, "state": run.current_state}


@router.get("/runs/{run_id}")
def run_state(run_id: str, db: DBSession = Depends(get_db)):
    run = get_run(db, run_id)
    if run is None:
        raise HTTPException(404, "unknown run_id")
    return {
        "run_id": run.run_id,
        "current_state": run.current_state,
        "previous_state": run.previous_state,
        "updated_at": run.updated_at,
    }


@router.get("/runs/{run_id}/history")
def run_history(run_id: str, db: DBSession = Depends(get_db)):
    if get_run(db, run_id) is None:
        raise HTTPException(404, "unknown run_id")
    return [
        {"from": t.from_state, "to": t.to_state, "reason": t.reason, "at": t.created_at}
        for t in history(db, run_id)
    ]


@router.post("/runs/{run_id}/resume")
def resume(run_id: str, db: DBSession = Depends(get_db)):
    """State lives in SQLite, so resuming is just reading it back."""
    run = get_run(db, run_id)
    if run is None:
        raise HTTPException(404, "unknown run_id")
    hints = {
        RunState.INPUT.value: "POST /api/v1/profiling/run",
        RunState.PROFILING.value: "POST /api/v1/matching/run",
        RunState.MATCHING.value: "POST /api/v1/matching/run",
        RunState.WAITING_FOR_APPROVAL.value: "POST /api/v1/matching/{match_id}/approve",
        RunState.SESSION.value: "POST /api/v1/sessions/generate",
        RunState.EVALUATION.value: "POST /api/v1/evaluations/{session_id}/generate",
        RunState.UPDATED_PROFILE.value: "run finished on next transition",
        RunState.NO_MATCH_FOUND.value: "no eligible group; seed more students or relax thresholds",
        RunState.FINISHED.value: "nothing to resume",
    }
    return {"run_id": run_id, "current_state": run.current_state, "next_action": hints[run.current_state]}


@router.get("/analytics/overview")
def overview(db: DBSession = Depends(get_db)):
    gains = db.query(LearningGain).all()
    effective = sum(1 for g in gains if g.effective)
    return {
        "students": db.query(Student).count(),
        "concepts": db.query(Concept).count(),
        "active_edges": len(G.edges(db)),
        "matches": db.query(MatchCandidate).count(),
        "sessions": db.query(Session).count(),
        "evaluations": db.query(Evaluation).count(),
        "average_learning_gain": round(sum(g.gain for g in gains) / len(gains), 4) if gains else 0.0,
        "effective_sessions": effective,
        "ineffective_sessions": len(gains) - effective,
        "graph_health": G.graph_health(db),
    }
