"""Typed domain models.

Every message that crosses a step boundary in ConceptBridge is one of
these models, never free-form prose. They are strict and JSON
serialisable.
"""

from __future__ import annotations

from slice.compat import BaseModel, Field


# --------------------------------------------------------------- states
class State:
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

    ALL = [
        INPUT, PROFILING, MATCHING, WAITING_FOR_APPROVAL, SESSION,
        EVALUATION, UPDATED_PROFILE, FINISHED, NO_SUITABLE_MATCH, FAILED,
    ]
    TERMINAL = {FINISHED, NO_SUITABLE_MATCH, FAILED}


# --------------------------------------------------------------- models
class ConceptScore(BaseModel):
    concept: str
    score: float


class StudentProfile(BaseModel):
    student_id: str
    student_name: str
    concepts: list[ConceptScore]

    # -- convenience (pure python, no validation impact) -----------
    def score_for(self, concept: str) -> float:
        for item in self.concepts:
            if item.concept == concept:
                return item.score
        raise KeyError(f"{self.student_id} has no score for concept {concept!r}")

    def as_dict(self) -> dict:
        return {item.concept: item.score for item in self.concepts}

    def with_score(self, concept: str, new_score: float) -> "StudentProfile":
        """Return a copy with one concept replaced (profiles stay immutable)."""
        updated = [
            ConceptScore(concept=c.concept,
                         score=new_score if c.concept == concept else c.score)
            for c in self.concepts
        ]
        return StudentProfile(student_id=self.student_id,
                              student_name=self.student_name,
                              concepts=updated)


class MatchCandidate(BaseModel):
    match_id: str
    student_a: str
    student_b: str
    compatibility_score: float
    a_teaches: list[str]
    b_teaches: list[str]
    rationale: str
    # deterministic score components (audit trail for the number above)
    a_to_b_score: float = 0.0
    b_to_a_score: float = 0.0
    balance: float = 0.0


class MatchCandidates(BaseModel):
    items: list[MatchCandidate]


class MatchExplanation(BaseModel):
    """Natural-language layer over an already-computed match. LLM output."""

    match_id: str
    summary: str
    a_teaches_reason: str
    b_teaches_reason: str


class Approval(BaseModel):
    match_id: str
    approved: bool
    answered_by: str


class SessionPlan(BaseModel):
    match_id: str
    learning_objectives: list[str]
    teaching_directions: list[str]
    teaching_prompts: list[str]
    shared_challenge: str
    follow_up_questions: list[str]


class LearningOutcome(BaseModel):
    student_id: str
    concept: str
    before_score: float
    after_score: float
    gain: float


class SessionOutcome(BaseModel):
    match_id: str
    outcomes: list[LearningOutcome]
    effective: bool


class ProfileUpdate(BaseModel):
    student_id: str
    concept: str
    old_score: float
    new_score: float
    gain: float


class Failure(BaseModel):
    reason: str
    state: str


class RunInput(BaseModel):
    """What the run was started with (recorded as the `input` record)."""

    run_id: str
    quiz_path: str
    concept_map_path: str
    scenario: str = "success"
    students: list[str] = Field(default_factory=list)
    mode: str = "stub"
