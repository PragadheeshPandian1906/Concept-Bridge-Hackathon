"""Append-only record model.

Every meaningful intermediate result in a run is written as one record.
Records are never mutated or overwritten, which makes a run replayable.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from .compat import BaseModel, Field


class RecordKind:
    """Canonical record kinds used by the ConceptBridge demo agent."""

    INPUT = "input"
    STUDENT_PROFILE = "student_profile"
    MATCH_CANDIDATE = "match_candidate"
    MATCH_EXPLANATION = "match_explanation"
    APPROVAL = "approval"
    SESSION = "session"
    OUTCOME = "outcome"
    PROFILE_UPDATE = "profile_update"
    FAILURE = "failure"
    STATE_TRANSITION = "state_transition"
    LLM_CALL = "llm_call"
    NOTE = "note"


class Record(BaseModel):
    """One immutable entry in the run history."""

    record_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = Field(default_factory=time.time)
    run_id: str = ""
    state: str = ""
    kind: str = RecordKind.NOTE
    version: int = 0
    payload: dict = Field(default_factory=dict)

    def summary(self) -> str:
        return f"[{self.state:<20}] {self.kind}"


def new_run_id(prefix: str = "cb") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def make_record(run_id: str, state: str, kind: str, payload: Any = None,
                version: int = 0) -> Record:
    if payload is None:
        payload = {}
    elif isinstance(payload, BaseModel):
        payload = payload.model_dump()
    elif not isinstance(payload, dict):
        payload = {"value": payload}
    return Record(run_id=run_id, state=state, kind=kind, payload=payload, version=version)
