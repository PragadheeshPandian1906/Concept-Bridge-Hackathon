"""Typed contracts between steps. Nothing important moves as free-form prose."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------- Profiling agent (LLM: open-ended answers only) ----------
class OpenEndedScore(BaseModel):
    score: float = Field(ge=0, le=5)
    normalized_score: float = Field(ge=0.0, le=1.0)
    strengths: list[str] = []
    missing_points: list[str] = []
    misconceptions: list[str] = []


# ---------- Matchmaking agent (deterministic, no LLM) ----------
class Relationship(BaseModel):
    teacher: str
    learner: str
    concept_id: str
    concept: str
    teacher_score: float
    learner_score: float
    gap: float


class GroupProperties(BaseModel):
    knowledge_cycle: bool
    reciprocal_relationships: int
    knowledge_coverage: float
    fairness_score: float
    observed_effectiveness: float
    previous_match_penalty: float
    teaching_load_penalty: float


class GroupCandidate(BaseModel):
    members: list[str]
    relationships: list[Relationship]
    properties: GroupProperties
    score: float
    components: dict


# ---------- Peer learning agent (LLM) ----------
class SessionRoundPlan(BaseModel):
    teacher: str
    learner: str
    concept: str
    objective: str
    explanation: str
    example: str
    activity: str
    understanding_check: str


class SessionPlan(BaseModel):
    objective: str
    rounds: list[SessionRoundPlan]


# ---------- Evaluation agent (LLM question generation) ----------
class EvalQuestion(BaseModel):
    question_id: str
    concept: str
    type: Literal["MCQ", "OPEN_ENDED"]
    text: str
    options: list[str] = []
    correct_answer: str | None = None
    rubric: str | None = None
    max_marks: int = 1


class EvalQuestionSet(BaseModel):
    questions: list[EvalQuestion]
