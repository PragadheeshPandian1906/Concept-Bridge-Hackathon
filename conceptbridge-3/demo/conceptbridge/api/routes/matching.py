from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ... import orchestrator
from ...persistence.database import get_db
from ...persistence.models import MatchCandidate
from ...state import get_run
from ..schemas import DecisionIn, MatchingIn

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/run")
def run_matching(payload: MatchingIn, db: DBSession = Depends(get_db)):
    if get_run(db, payload.run_id) is None:
        raise HTTPException(404, "unknown run_id")
    try:
        return orchestrator.run_matching(db, payload.run_id, payload.student_ids)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/current")
def current(run_id: str | None = None, db: DBSession = Depends(get_db)):
    query = db.query(MatchCandidate).filter(MatchCandidate.status == "PROPOSED")
    if run_id:
        query = query.filter(MatchCandidate.run_id == run_id)
    match = query.order_by(MatchCandidate.created_at.desc()).first()
    if match is None:
        raise HTTPException(404, "no proposed match")
    return orchestrator._match_dict(match)


@router.get("/history")
def history(db: DBSession = Depends(get_db)):
    rows = db.query(MatchCandidate).order_by(MatchCandidate.created_at.desc()).all()
    return [orchestrator._match_dict(m) for m in rows]


@router.post("/{match_id}/approve")
def approve(match_id: str, payload: DecisionIn, db: DBSession = Depends(get_db)):
    if db.get(MatchCandidate, match_id) is None:
        raise HTTPException(404, "unknown match")
    try:
        return orchestrator.approve_match(db, match_id, payload.decided_by, payload.reason)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{match_id}/reject")
def reject(match_id: str, payload: DecisionIn, db: DBSession = Depends(get_db)):
    if db.get(MatchCandidate, match_id) is None:
        raise HTTPException(404, "unknown match")
    try:
        return orchestrator.reject_match(db, match_id, payload.decided_by, payload.reason)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
