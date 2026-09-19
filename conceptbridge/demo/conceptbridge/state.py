"""Deterministic, persistent state machine. No LLM ever decides a transition."""
from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum

from sqlalchemy.orm import Session as DBSession

from .persistence.models import StateRun, StateTransition


class RunState(str, Enum):
    INPUT = "INPUT"
    PROFILING = "PROFILING"
    MATCHING = "MATCHING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    SESSION = "SESSION"
    EVALUATION = "EVALUATION"
    UPDATED_PROFILE = "UPDATED_PROFILE"
    FINISHED = "FINISHED"
    NO_MATCH_FOUND = "NO_MATCH_FOUND"


ALLOWED: dict[RunState, set[RunState]] = {
    RunState.INPUT: {RunState.PROFILING},
    RunState.PROFILING: {RunState.MATCHING},
    RunState.MATCHING: {RunState.WAITING_FOR_APPROVAL, RunState.NO_MATCH_FOUND},
    RunState.WAITING_FOR_APPROVAL: {RunState.SESSION, RunState.MATCHING},
    RunState.SESSION: {RunState.EVALUATION},
    RunState.EVALUATION: {RunState.UPDATED_PROFILE, RunState.MATCHING},
    RunState.UPDATED_PROFILE: {RunState.FINISHED},
    RunState.NO_MATCH_FOUND: {RunState.FINISHED},
    RunState.FINISHED: set(),
}


class InvalidTransition(RuntimeError):
    pass


def create_run(db: DBSession, run_id: str | None = None, meta: dict | None = None) -> StateRun:
    run_id = run_id or f"RUN-{uuid.uuid4().hex[:8].upper()}"
    run = StateRun(run_id=run_id, current_state=RunState.INPUT.value, meta=meta or {})
    db.add(run)
    db.add(StateTransition(run_id=run_id, from_state=None, to_state=RunState.INPUT.value, reason="run created"))
    db.commit()
    return run


def get_run(db: DBSession, run_id: str) -> StateRun | None:
    return db.get(StateRun, run_id)


def load_state(db: DBSession, run_id: str) -> RunState:
    run = get_run(db, run_id)
    if run is None:
        raise KeyError(f"unknown run_id {run_id}")
    return RunState(run.current_state)


def transition(db: DBSession, run_id: str, to_state: RunState, reason: str = "") -> StateRun:
    run = get_run(db, run_id)
    if run is None:
        raise KeyError(f"unknown run_id {run_id}")
    current = RunState(run.current_state)
    if to_state not in ALLOWED[current]:
        raise InvalidTransition(f"{current.value} -> {to_state.value} is not allowed")
    run.previous_state = current.value
    run.current_state = to_state.value
    run.updated_at = dt.datetime.now(dt.timezone.utc)
    db.add(StateTransition(run_id=run_id, from_state=current.value, to_state=to_state.value, reason=reason))
    db.commit()
    return run


def history(db: DBSession, run_id: str) -> list[StateTransition]:
    return (
        db.query(StateTransition)
        .filter(StateTransition.run_id == run_id)
        .order_by(StateTransition.id.asc())
        .all()
    )
