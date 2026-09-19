from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class State(str, Enum):
    INPUT = "INPUT"
    PROFILING = "PROFILING"
    MATCHING = "MATCHING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    SESSION = "SESSION"
    EVALUATION = "EVALUATION"
    UPDATED_PROFILE = "UPDATED_PROFILE"
    FINISHED = "FINISHED"
    NO_SUITABLE_MATCH = "NO_SUITABLE_MATCH"
    FAILED = "FAILED"


class ConceptScore(BaseModel):
    concept: str
    score: float = Field(ge=0, le=1)


class StudentProfile(BaseModel):
    student_id: str
    student_name: str
    concepts: list[ConceptScore]


class MatchCandidate(BaseModel):
    match_id: str
    student_a: str
    student_b: str
    compatibility_score: float = Field(ge=0, le=1)
    a_teaches: list[str]
    b_teaches: list[str]
    rationale: str
    score_components: dict[str, float] = Field(default_factory=dict)


class MatchCandidates(BaseModel):
    items: list[MatchCandidate]


class Approval(BaseModel):
    match_id: str
    approved: bool
    answered_by: str


class LearningOutcome(BaseModel):
    student_id: str
    concept: str
    before_score: float = Field(ge=0, le=1)
    after_score: float = Field(ge=0, le=1)
    gain: float


class SessionOutcome(BaseModel):
    match_id: str
    outcomes: list[LearningOutcome]
    effective: bool


class SessionPlan(BaseModel):
    match_id: str
    learning_objectives: list[str]
    teaching_directions: list[str]
    teaching_prompts: list[str]
    shared_challenge: str
    follow_up_questions: list[str]


class ProfileUpdate(BaseModel):
    student_id: str
    concept: str
    old_score: float
    new_score: float
    gain: float


class Failure(BaseModel):
    reason: str
    state: str