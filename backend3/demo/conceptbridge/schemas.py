from typing import Any, Literal
from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    id: str
    name: str
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConceptCreate(BaseModel):
    id: str
    name: str
    description: str = ""


class ScoreUpsert(BaseModel):
    concept_id: str
    score: float = Field(ge=0, le=1)
    source: str = "manual"


class QuestionCreate(BaseModel):
    id: str
    concept_id: str
    type: Literal["mcq", "open"]
    text: str
    correct_answer: str | None = None
    max_marks: float = Field(default=1, gt=0, le=5)
    rubric: str = ""


class AnswerSubmit(BaseModel):
    student_id: str
    answer: str


class RejectRequest(BaseModel):
    actor: str = "human"
    reason: str | None = None


class ApproveRequest(BaseModel):
    actor: str = "human"
    duration_minutes: int = Field(default=45, ge=15, le=240)


class EvaluationSubmit(BaseModel):
    """Post-session concept scores; server calculates gains and effectiveness."""
    post_scores: dict[str, float] = Field(min_length=1)


class EvaluationBatchItem(EvaluationSubmit):
    evaluation_id: str


class EvaluationBatchSubmit(BaseModel):
    evaluations: list[EvaluationBatchItem] = Field(min_length=1)
