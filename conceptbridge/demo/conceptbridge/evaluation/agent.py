"""Agent 4 - Evaluation: 'did learning actually occur?'

The LLM writes questions and grades prose. Python owns every number that matters.
"""
from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from slice.budget import Budget
from slice.llm import complete

from ..config import get_config
from ..persistence.models import (
    Concept,
    ConceptScore,
    EdgeStat,
    Evaluation,
    LearningGain,
    ProfileUpdate,
    Session,
    SessionRound,
)
from ..profiling.scoring import score_mcq
from ..profiling.stub import stub_open_ended
from ..schema import EvalQuestionSet, OpenEndedScore
from .scoring import average, is_effective, learning_gain
from .stub import stub_questions

PROMPT = (Path(__file__).parent / "prompts" / "questions.md").read_text()


def generate_evaluation(db: DBSession, session_id: str, budget: Budget | None = None) -> Evaluation:
    cfg = get_config()
    session = db.get(Session, session_id)
    if session is None:
        raise KeyError(f"unknown session {session_id}")
    names = {c.id: c.name for c in db.query(Concept).all()}
    rounds = db.query(SessionRound).filter(SessionRound.session_id == session_id).all()
    taught = [{"concept_id": r.concept_id, "concept": names.get(r.concept_id, r.concept_id)} for r in rounds]

    messages = [
        {"role": "system", "content": PROMPT},
        {
            "role": "user",
            "content": (
                f"CONCEPTS TAUGHT: {json.dumps(taught)}\n"
                f"QUESTIONS PER CONCEPT: {cfg.questions_per_concept}\n"
                f"SESSION PLAN (do not reuse these examples): {json.dumps(session.plan)[:3000]}"
            ),
        },
    ]
    question_set = complete(
        messages=messages,
        schema=EvalQuestionSet,
        step="evaluation:questions",
        stub=lambda: stub_questions(taught, cfg.questions_per_concept),
        budget=budget or Budget(),
    )

    # attach concept_id back onto each question so scoring stays deterministic
    reverse = {v: k for k, v in names.items()}
    payload = []
    for q in question_set.questions:
        item = q.model_dump()
        item["concept_id"] = reverse.get(q.concept, q.concept)
        payload.append(item)

    evaluation = Evaluation(
        id=f"EVAL-{uuid.uuid4().hex[:8].upper()}",
        session_id=session.id,
        run_id=session.run_id,
        status="GENERATED",
        questions=payload,
    )
    db.add(evaluation)
    db.commit()
    return evaluation


def public_questions(evaluation: Evaluation) -> list[dict]:
    """Same questions, without the answer key."""
    out = []
    for q in evaluation.questions:
        item = {k: v for k, v in q.items() if k not in {"correct_answer", "rubric"}}
        out.append(item)
    return out


def submit_evaluation(db: DBSession, evaluation_id: str, answers: list[dict], budget: Budget | None = None) -> dict:
    """answers = [{"question_id": ..., "student_id": ..., "answer": ...}]"""
    cfg = get_config()
    budget = budget or Budget()
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise KeyError(f"unknown evaluation {evaluation_id}")
    if evaluation.status == "SUBMITTED":
        raise ValueError("evaluation already submitted")

    questions = {q["question_id"]: q for q in evaluation.questions}
    session = db.get(Session, evaluation.session_id)
    rounds = db.query(SessionRound).filter(SessionRound.session_id == session.id).all()
    learner_of_concept = {r.concept_id: (r.learner, r.teacher, r.pre_score) for r in rounds}

    per_concept: dict[str, list[float]] = {}
    for ans in answers:
        question = questions.get(ans["question_id"])
        if question is None:
            continue
        if question["type"] == "MCQ":
            normalized = score_mcq(ans.get("answer"), question.get("correct_answer"))
        else:
            graded = complete(
                messages=[
                    {"role": "system", "content": "Grade this open-ended answer. Return only the JSON object."},
                    {
                        "role": "user",
                        "content": (
                            f"QUESTION: {question['text']}\nRUBRIC: {question.get('rubric','')}\n"
                            f"MAX MARKS: {question.get('max_marks',5)}\nSTUDENT ANSWER: {ans.get('answer','')}"
                        ),
                    },
                ],
                schema=OpenEndedScore,
                step="evaluation:open_ended",
                stub=lambda q=question, a=ans: stub_open_ended(
                    q["text"], q.get("rubric", ""), a.get("answer", ""), q.get("max_marks", 5)
                ),
                budget=budget,
            )
            normalized = graded.normalized_score
        per_concept.setdefault(question["concept_id"], []).append(normalized)

    gains = []
    for concept_id, values in per_concept.items():
        if concept_id not in learner_of_concept:
            continue
        learner, teacher, pre = learner_of_concept[concept_id]
        post = average(values)
        gain = learning_gain(pre, post)
        effective = is_effective(gain, cfg.effective_gain_threshold)
        db.add(
            LearningGain(
                session_id=session.id,
                teacher=teacher,
                learner=learner,
                concept_id=concept_id,
                pre_score=pre,
                post_score=post,
                gain=gain,
                effective=effective,
            )
        )
        _update_edge_stat(db, teacher, learner, concept_id, gain, effective)
        gains.append(
            {
                "teacher": teacher,
                "learner": learner,
                "concept_id": concept_id,
                "pre_score": pre,
                "post_score": post,
                "gain": gain,
                "effective": effective,
            }
        )

    overall_gain = average([g["gain"] for g in gains])
    overall_effective = is_effective(overall_gain, cfg.effective_gain_threshold)
    evaluation.answers = answers
    evaluation.status = "SUBMITTED"
    evaluation.submitted_at = dt.datetime.now(dt.timezone.utc)
    evaluation.result = {
        "per_concept": gains,
        "average_gain": overall_gain,
        "effective": overall_effective,
        "threshold": cfg.effective_gain_threshold,
    }
    db.commit()
    return evaluation.result


def _update_edge_stat(db: DBSession, teacher: str, learner: str, concept_id: str, gain: float, effective: bool) -> None:
    stat = (
        db.query(EdgeStat)
        .filter(
            EdgeStat.source_student == teacher,
            EdgeStat.target_student == learner,
            EdgeStat.concept_id == concept_id,
        )
        .one_or_none()
    )
    if stat is None:
        stat = EdgeStat(source_student=teacher, target_student=learner, concept_id=concept_id)
        db.add(stat)
    stat.sessions = (stat.sessions or 0) + 1
    stat.successful_sessions = (stat.successful_sessions or 0) + (1 if effective else 0)
    stat.total_gain = round((stat.total_gain or 0.0) + gain, 4)


def apply_profile_updates(db: DBSession, session_id: str) -> list[dict]:
    """Write post-session scores into the learner profiles. History is preserved."""
    updates = []
    for gain in db.query(LearningGain).filter(LearningGain.session_id == session_id).all():
        row = (
            db.query(ConceptScore)
            .filter(ConceptScore.student_id == gain.learner, ConceptScore.concept_id == gain.concept_id)
            .one_or_none()
        )
        old = float(row.score) if row else 0.0
        new = max(old, gain.post_score) if gain.gain > 0 else old
        if row is None:
            db.add(ConceptScore(student_id=gain.learner, concept_id=gain.concept_id, score=new, source="session"))
        else:
            row.score = new
            row.source = "session"
        db.add(
            ProfileUpdate(
                student_id=gain.learner,
                concept_id=gain.concept_id,
                old_score=old,
                new_score=new,
                gain=round(new - old, 4),
                source="session",
                session_id=session_id,
            )
        )
        updates.append(
            {"student_id": gain.learner, "concept_id": gain.concept_id, "old_score": old, "new_score": round(new, 4)}
        )
    db.commit()
    return updates
