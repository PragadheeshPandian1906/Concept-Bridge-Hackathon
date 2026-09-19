from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ... import orchestrator
from ...evaluation import agent as evaluation_agent
from ...peer_learning import agent as peer_agent
from ...persistence.database import get_db
from ...persistence.models import Evaluation, Session, SessionRound
from ..schemas import EvalSubmission, SessionIn

router = APIRouter(tags=["sessions"])


def _session_dict(db: DBSession, session: Session) -> dict:
    rounds = db.query(SessionRound).filter(SessionRound.session_id == session.id).all()
    return {
        "id": session.id,
        "run_id": session.run_id,
        "match_id": session.match_id,
        "status": session.status,
        "plan": session.plan,
        "rounds": [
            {
                "teacher": r.teacher,
                "learner": r.learner,
                "concept_id": r.concept_id,
                "pre_score": r.pre_score,
                "status": r.status,
                "content": r.content,
            }
            for r in rounds
        ],
    }


@router.post("/sessions/generate")
def generate(payload: SessionIn, db: DBSession = Depends(get_db)):
    try:
        session = orchestrator.generate_session(db, payload.match_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return _session_dict(db, session)


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(Session, session_id)
    if session is None:
        raise HTTPException(404, "unknown session")
    return _session_dict(db, session)


@router.post("/sessions/{session_id}/start")
def start(session_id: str, db: DBSession = Depends(get_db)):
    if db.get(Session, session_id) is None:
        raise HTTPException(404, "unknown session")
    return _session_dict(db, peer_agent.start_session(db, session_id))


@router.post("/sessions/{session_id}/complete")
def complete(session_id: str, db: DBSession = Depends(get_db)):
    if db.get(Session, session_id) is None:
        raise HTTPException(404, "unknown session")
    try:
        return _session_dict(db, orchestrator.complete_session(db, session_id))
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/evaluations/{session_id}/generate")
def generate_evaluation(session_id: str, db: DBSession = Depends(get_db)):
    if db.get(Session, session_id) is None:
        raise HTTPException(404, "unknown session")
    evaluation = evaluation_agent.generate_evaluation(db, session_id)
    return {
        "id": evaluation.id,
        "session_id": evaluation.session_id,
        "status": evaluation.status,
        "questions": evaluation_agent.public_questions(evaluation),
    }


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str, db: DBSession = Depends(get_db)):
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise HTTPException(404, "unknown evaluation")
    return {
        "id": evaluation.id,
        "session_id": evaluation.session_id,
        "status": evaluation.status,
        "questions": evaluation_agent.public_questions(evaluation),
        "result": evaluation.result,
    }


@router.post("/evaluations/{evaluation_id}/submit")
def submit_evaluation(evaluation_id: str, payload: EvalSubmission, db: DBSession = Depends(get_db)):
    if db.get(Evaluation, evaluation_id) is None:
        raise HTTPException(404, "unknown evaluation")
    try:
        return orchestrator.submit_evaluation(db, evaluation_id, [a.model_dump() for a in payload.answers])
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
