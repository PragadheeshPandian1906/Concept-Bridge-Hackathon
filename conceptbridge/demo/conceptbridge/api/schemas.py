from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StudentIn(BaseModel):
    id: str
    name: str
    email: str | None = None


class ConceptIn(BaseModel):
    id: str
    name: str
    description: str = ""


class QuestionIn(BaseModel):
    id: str
    concept_id: str
    type: Literal["MCQ", "OPEN_ENDED"]
    text: str
    max_marks: int = 1
    options: list[str] = []
    correct_answer: str | None = None
    rubric: str | None = None


class AnswerIn(BaseModel):
    student_id: str
    question_id: str
    answer: str


class QuizSubmission(BaseModel):
    run_id: str | None = None
    answers: list[AnswerIn] = Field(min_length=1)


class RunIn(BaseModel):
    run_id: str


class MatchingIn(BaseModel):
    run_id: str
    student_ids: list[str] | None = None


class DecisionIn(BaseModel):
    decided_by: str = "instructor"
    reason: str = ""


class SessionIn(BaseModel):
    match_id: str


class EvalAnswerIn(BaseModel):
    question_id: str
    answer: str


class EvalSubmission(BaseModel):
    answers: list[EvalAnswerIn] = Field(min_length=1)
