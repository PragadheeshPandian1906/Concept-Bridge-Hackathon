"""Agent 1 - Concept Profiling: 'What does the student know?'"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from slice.budget import Budget
from slice.llm import complete

from ..persistence.models import ConceptScore, Question, Student, StudentAnswer
from ..schema import OpenEndedScore
from .scoring import aggregate_by_concept, normalize, score_mcq
from .stub import stub_open_ended

PROMPT = (Path(__file__).parent / "prompts" / "score_open_ended.md").read_text()


def _grade_open_ended(question: Question, answer: str, budget: Budget) -> OpenEndedScore:
    messages = [
        {"role": "system", "content": PROMPT.replace("{max_marks}", str(question.max_marks))},
        {
            "role": "user",
            "content": (
                f"CONCEPT: {question.concept_id}\n"
                f"QUESTION: {question.text}\n"
                f"MODEL ANSWER / RUBRIC: {question.rubric or ''}\n"
                f"MAX MARKS: {question.max_marks}\n"
                f"STUDENT ANSWER: {answer}"
            ),
        },
    ]
    return complete(
        messages=messages,
        schema=OpenEndedScore,
        step="profiling:open_ended",
        stub=lambda: stub_open_ended(question.text, question.rubric or "", answer, question.max_marks),
        budget=budget,
    )


def run_profiling(db: DBSession, run_id: str | None = None, budget: Budget | None = None) -> dict:
    """Score every unscored answer and rebuild concept vectors."""
    budget = budget or Budget()
    query = db.query(StudentAnswer)
    if run_id:
        query = query.filter(StudentAnswer.run_id == run_id)
    answers = query.all()

    llm_calls = 0
    for ans in answers:
        question = db.get(Question, ans.question_id)
        if question is None:
            continue
        if question.type == "MCQ":
            ans.score = score_mcq(ans.answer, question.correct_answer)
            ans.normalized_score = normalize(ans.score, 1)
            ans.detail = {"method": "deterministic"}
        else:
            graded = _grade_open_ended(question, ans.answer or "", budget)
            llm_calls += 1
            ans.score = graded.score
            ans.normalized_score = graded.normalized_score
            ans.detail = graded.model_dump()
    db.commit()

    scope = {a.student_id for a in answers} if run_id else {s.id for s in db.query(Student).all()}
    profiles: dict[str, dict[str, float]] = {}
    for student in db.query(Student).filter(Student.id.in_(scope or {""})).all():
        rows = (
            db.query(StudentAnswer.question_id, StudentAnswer.normalized_score)
            .filter(StudentAnswer.student_id == student.id)
            .all()
        )
        pairs: list[tuple[str, float]] = []
        for question_id, value in rows:
            question = db.get(Question, question_id)
            if question and value is not None:
                pairs.append((question.concept_id, value))
        if not pairs:
            continue
        vector = aggregate_by_concept(pairs)
        profiles[student.id] = vector
        for concept_id, score in vector.items():
            row = (
                db.query(ConceptScore)
                .filter(ConceptScore.student_id == student.id, ConceptScore.concept_id == concept_id)
                .one_or_none()
            )
            if row is None:
                db.add(ConceptScore(student_id=student.id, concept_id=concept_id, score=score, source="quiz"))
            else:
                row.score = score
                row.source = "quiz"
    db.commit()
    return {"students_profiled": len(profiles), "llm_calls": llm_calls, "profiles": profiles}


def get_profile(db: DBSession, student_id: str) -> dict[str, float]:
    rows = db.query(ConceptScore).filter(ConceptScore.student_id == student_id).all()
    return {r.concept_id: round(r.score, 4) for r in rows}


def all_profiles(db: DBSession) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in db.query(ConceptScore).all():
        out.setdefault(row.student_id, {})[row.concept_id] = round(row.score, 4)
    return out
