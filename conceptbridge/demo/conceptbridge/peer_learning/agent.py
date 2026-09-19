"""Agent 3 - Peer Learning: 'how should they teach and learn?'"""
from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from slice.budget import Budget
from slice.llm import complete

from ..persistence.models import ConceptScore, MatchCandidate, Session, SessionRound
from ..schema import SessionPlan
from .stub import stub_session

PROMPT = (Path(__file__).parent / "prompts" / "session.md").read_text()


def _pre_score(db: DBSession, student_id: str, concept_id: str) -> float:
    row = (
        db.query(ConceptScore)
        .filter(ConceptScore.student_id == student_id, ConceptScore.concept_id == concept_id)
        .one_or_none()
    )
    return float(row.score) if row else 0.0


def generate_session(db: DBSession, match_id: str, budget: Budget | None = None) -> Session:
    match = db.get(MatchCandidate, match_id)
    if match is None:
        raise KeyError(f"unknown match {match_id}")
    if match.status != "APPROVED":
        raise ValueError(f"match {match_id} is {match.status}, not APPROVED")

    rels = match.relationships
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": "GROUP: " + json.dumps(match.members) + "\nRELATIONSHIPS: " + json.dumps(rels)},
    ]
    plan = complete(
        messages=messages,
        schema=SessionPlan,
        step="peer_learning:session",
        stub=lambda: stub_session(rels),
        budget=budget or Budget(),
    )

    session = Session(
        id=f"SES-{uuid.uuid4().hex[:8].upper()}",
        run_id=match.run_id,
        match_id=match.id,
        status="CREATED",
        plan=plan.model_dump(),
    )
    db.add(session)
    db.flush()
    for rel, round_plan in zip(rels, plan.rounds):
        db.add(
            SessionRound(
                session_id=session.id,
                teacher=rel["teacher"],
                learner=rel["learner"],
                concept_id=rel["concept_id"],
                pre_score=_pre_score(db, rel["learner"], rel["concept_id"]),
                content=round_plan.model_dump(),
                status="PLANNED",
            )
        )
    db.commit()
    return session


def start_session(db: DBSession, session_id: str) -> Session:
    session = db.get(Session, session_id)
    session.status = "STARTED"
    session.started_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return session


def complete_session(db: DBSession, session_id: str) -> Session:
    session = db.get(Session, session_id)
    session.status = "COMPLETED"
    session.completed_at = dt.datetime.now(dt.timezone.utc)
    for rnd in db.query(SessionRound).filter(SessionRound.session_id == session_id).all():
        rnd.status = "COMPLETED"
    db.commit()
    return session
