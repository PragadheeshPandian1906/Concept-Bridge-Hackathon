"""Students, concepts, questions, quiz submission, profiling."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ... import orchestrator
from ...persistence.database import get_db
from ...persistence.models import Concept, Question, Student, StudentAnswer
from ...profiling import agent as profiling_agent
from ...state import RunState, create_run, get_run
from ..schemas import ConceptIn, QuestionIn, QuizSubmission, RunIn, StudentIn

router = APIRouter()


@router.post("/students", tags=["students"])
def create_student(payload: StudentIn, db: DBSession = Depends(get_db)):
    db.merge(Student(id=payload.id, name=payload.name, email=payload.email, meta={}))
    db.commit()
    return payload.model_dump()


@router.get("/students", tags=["students"])
def list_students(db: DBSession = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "email": s.email} for s in db.query(Student).all()]


@router.get("/students/{student_id}", tags=["students"])
def get_student(student_id: str, db: DBSession = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "student not found")
    return {"id": student.id, "name": student.name, "email": student.email}


@router.get("/students/{student_id}/profile", tags=["profiles"])
def student_profile(student_id: str, db: DBSession = Depends(get_db)):
    if not db.get(Student, student_id):
        raise HTTPException(404, "student not found")
    return {"student_id": student_id, "concept_scores": profiling_agent.get_profile(db, student_id)}


@router.get("/profiles", tags=["profiles"])
def all_profiles(db: DBSession = Depends(get_db)):
    return profiling_agent.all_profiles(db)


@router.post("/concepts", tags=["concepts"])
def create_concept(payload: ConceptIn, db: DBSession = Depends(get_db)):
    db.merge(Concept(**payload.model_dump()))
    db.commit()
    return payload.model_dump()


@router.get("/concepts", tags=["concepts"])
def list_concepts(db: DBSession = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "description": c.description} for c in db.query(Concept).all()]


@router.post("/questions", tags=["questions"])
def create_question(payload: QuestionIn, db: DBSession = Depends(get_db)):
    if not db.get(Concept, payload.concept_id):
        raise HTTPException(400, "unknown concept_id")
    db.merge(Question(**payload.model_dump()))
    db.commit()
    return payload.model_dump()


@router.get("/questions", tags=["questions"])
def list_questions(db: DBSession = Depends(get_db)):
    return [
        {"id": q.id, "concept_id": q.concept_id, "type": q.type, "text": q.text, "max_marks": q.max_marks}
        for q in db.query(Question).all()
    ]


@router.post("/quiz/submit", tags=["quiz"])
def submit_quiz(payload: QuizSubmission, db: DBSession = Depends(get_db)):
    run_id = payload.run_id
    if run_id is None or get_run(db, run_id) is None:
        run = create_run(db, run_id)
        run_id = run.run_id
    for item in payload.answers:
        if not db.get(Student, item.student_id):
            raise HTTPException(400, f"unknown student {item.student_id}")
        if not db.get(Question, item.question_id):
            raise HTTPException(400, f"unknown question {item.question_id}")
        db.add(
            StudentAnswer(
                run_id=run_id, student_id=item.student_id, question_id=item.question_id, answer=item.answer
            )
        )
    db.commit()
    return {"run_id": run_id, "stored": len(payload.answers), "state": RunState.INPUT.value}


@router.post("/profiling/run", tags=["profiling"])
def run_profiling(payload: RunIn, db: DBSession = Depends(get_db)):
    if get_run(db, payload.run_id) is None:
        raise HTTPException(404, "unknown run_id")
    try:
        return orchestrator.run_profiling(db, payload.run_id)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
