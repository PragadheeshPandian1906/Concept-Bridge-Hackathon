"""Relational source of truth. JSON columns are used only for generated artifacts."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from .database import Base


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    meta = Column(JSON, default=dict)


class Concept(Base):
    __tablename__ = "concepts"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")


class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True)
    concept_id = Column(String, ForeignKey("concepts.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # MCQ | OPEN_ENDED
    text = Column(Text, nullable=False)
    max_marks = Column(Integer, default=1)
    options = Column(JSON, default=list)
    correct_answer = Column(String)
    rubric = Column(Text)


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    question_id = Column(String, ForeignKey("questions.id"), index=True)
    answer = Column(Text)
    score = Column(Float)
    normalized_score = Column(Float)
    detail = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)


class ConceptScore(Base):
    """Current proficiency. One row per (student, concept)."""

    __tablename__ = "concept_scores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    concept_id = Column(String, ForeignKey("concepts.id"), index=True)
    score = Column(Float, nullable=False)
    source = Column(String, default="quiz")
    updated_at = Column(DateTime, default=now, onupdate=now)


class ProfileUpdate(Base):
    """Append-only history of every score change."""

    __tablename__ = "profile_updates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, index=True)
    concept_id = Column(String, index=True)
    old_score = Column(Float)
    new_score = Column(Float)
    gain = Column(Float)
    source = Column(String)
    session_id = Column(String)
    created_at = Column(DateTime, default=now)


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_student = Column(String, index=True)
    target_student = Column(String, index=True)
    active = Column(Boolean, default=True, index=True)
    edge_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class EdgeConcept(Base):
    __tablename__ = "edge_concepts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    edge_id = Column(Integer, ForeignKey("knowledge_edges.id"), index=True)
    concept_id = Column(String, index=True)
    teacher_score = Column(Float)
    learner_score = Column(Float)
    transfer_gap = Column(Float)


class EdgeStat(Base):
    """Observed history for a (teacher, learner, concept) triple. Never deleted."""

    __tablename__ = "edge_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_student = Column(String, index=True)
    target_student = Column(String, index=True)
    concept_id = Column(String, index=True)
    sessions = Column(Integer, default=0)
    successful_sessions = Column(Integer, default=0)
    total_gain = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=now, onupdate=now)


class MatchCandidate(Base):
    __tablename__ = "match_candidates"
    id = Column(String, primary_key=True)
    run_id = Column(String, index=True)
    members = Column(JSON, default=list)
    relationships = Column(JSON, default=list)
    properties = Column(JSON, default=dict)
    components = Column(JSON, default=dict)
    score = Column(Float)
    status = Column(String, default="PROPOSED")  # PROPOSED | APPROVED | REJECTED
    decided_by = Column(String)
    reason = Column(Text)
    created_at = Column(DateTime, default=now)
    decided_at = Column(DateTime)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    run_id = Column(String, index=True)
    match_id = Column(String, ForeignKey("match_candidates.id"), index=True)
    status = Column(String, default="CREATED")  # CREATED | STARTED | COMPLETED
    plan = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class SessionRound(Base):
    __tablename__ = "session_rounds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    teacher = Column(String)
    learner = Column(String)
    concept_id = Column(String)
    pre_score = Column(Float)
    content = Column(JSON, default=dict)
    status = Column(String, default="PLANNED")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    run_id = Column(String, index=True)
    status = Column(String, default="GENERATED")  # GENERATED | SUBMITTED
    questions = Column(JSON, default=list)
    answers = Column(JSON, default=list)
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)
    submitted_at = Column(DateTime)


class LearningGain(Base):
    __tablename__ = "learning_gains"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    teacher = Column(String)
    learner = Column(String)
    concept_id = Column(String)
    pre_score = Column(Float)
    post_score = Column(Float)
    gain = Column(Float)
    effective = Column(Boolean)
    created_at = Column(DateTime, default=now)


class StateRun(Base):
    __tablename__ = "state_runs"
    run_id = Column(String, primary_key=True)
    current_state = Column(String, nullable=False)
    previous_state = Column(String)
    retry_count = Column(Integer, default=0)
    error = Column(Text)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class StateTransition(Base):
    __tablename__ = "state_transitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, index=True)
    from_state = Column(String)
    to_state = Column(String)
    reason = Column(Text)
    created_at = Column(DateTime, default=now)
