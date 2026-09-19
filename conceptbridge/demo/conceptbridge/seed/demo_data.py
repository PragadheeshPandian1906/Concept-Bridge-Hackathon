"""Seed data engineered to produce an interesting graph:

reciprocal pair (S001 <-> S002), a 3-person knowledge cycle (S003 -> S004 -> S005 -> S003),
a knowledge hub (S006), a bottleneck concept (SQL Joins) and an isolated student (S008).
"""
from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from ..persistence.models import Concept, Question, Student, StudentAnswer

CONCEPTS = [
    ("C_REC", "Recursion"),
    ("C_ARR", "Arrays"),
    ("C_TRE", "Trees"),
    ("C_SQL", "SQL Joins"),
    ("C_NOR", "Normalization"),
    ("C_TRA", "Transactions"),
    ("C_OS", "Operating Systems"),
    ("C_NET", "Networking"),
]

STUDENTS = [
    ("S001", "Aarthi"),
    ("S002", "Bharath"),
    ("S003", "Chitra"),
    ("S004", "Dinesh"),
    ("S005", "Elango"),
    ("S006", "Farah"),
    ("S007", "Gokul"),
    ("S008", "Harini"),
]

# correct MCQs out of 5, per student per concept
MCQ_MATRIX = {
    "S001": {"C_REC": 5, "C_ARR": 4, "C_TRE": 4, "C_SQL": 1, "C_NOR": 1, "C_TRA": 3, "C_OS": 3, "C_NET": 3},
    "S002": {"C_REC": 1, "C_ARR": 3, "C_TRE": 1, "C_SQL": 5, "C_NOR": 4, "C_TRA": 3, "C_OS": 3, "C_NET": 3},
    "S003": {"C_REC": 3, "C_ARR": 3, "C_TRE": 5, "C_SQL": 1, "C_NOR": 1, "C_TRA": 1, "C_OS": 3, "C_NET": 3},
    "S004": {"C_REC": 3, "C_ARR": 3, "C_TRE": 1, "C_SQL": 1, "C_NOR": 5, "C_TRA": 1, "C_OS": 3, "C_NET": 3},
    "S005": {"C_REC": 3, "C_ARR": 3, "C_TRE": 1, "C_SQL": 1, "C_NOR": 1, "C_TRA": 5, "C_OS": 3, "C_NET": 3},
    "S006": {"C_REC": 4, "C_ARR": 5, "C_TRE": 5, "C_SQL": 1, "C_NOR": 3, "C_TRA": 3, "C_OS": 5, "C_NET": 5},
    "S007": {"C_REC": 1, "C_ARR": 1, "C_TRE": 1, "C_SQL": 1, "C_NOR": 1, "C_TRA": 1, "C_OS": 1, "C_NET": 1},
    "S008": {"C_REC": 3, "C_ARR": 3, "C_TRE": 3, "C_SQL": 3, "C_NOR": 3, "C_TRA": 3, "C_OS": 3, "C_NET": 3},
}

# concepts that also carry an open-ended (0-5) question -> exercises the LLM path
OPEN_CONCEPTS = {
    "C_REC": "recursion basecase recursive stack termination subproblem",
    "C_SQL": "inner outer join matching rows cartesian predicate",
}

# quality of each student's open-ended answer: strong / medium / weak
OPEN_QUALITY = {
    "C_REC": {"S001": "strong", "S006": "strong", "S008": "strong", "S002": "weak", "S007": "weak"},
    "C_SQL": {"S002": "strong", "S008": "strong", "S001": "weak", "S007": "weak"},
}

ANSWER_TEXT = {
    "strong": (
        "A recursion basecase stops the recursive descent; every recursive call must move toward "
        "termination by solving a smaller subproblem, and each pending call occupies a stack frame. "
        "An inner join keeps only matching rows, an outer join keeps unmatched rows too, and without "
        "a predicate you get a cartesian product across both tables."
    ),
    "medium": "It breaks the problem into smaller parts and stops at some point, joining rows that match.",
    "weak": "It calls itself again and again.",
}


def seed(db: DBSession) -> dict:
    for cid, name in CONCEPTS:
        db.merge(Concept(id=cid, name=name, description=f"{name} fundamentals"))
    for sid, name in STUDENTS:
        db.merge(Student(id=sid, name=name, email=f"{name.lower()}@example.edu", meta={}))
    db.commit()

    for cid, _name in CONCEPTS:
        for i in range(1, 6):
            db.merge(
                Question(
                    id=f"Q-{cid}-{i}",
                    concept_id=cid,
                    type="MCQ",
                    text=f"[{cid}] Multiple-choice question {i}",
                    max_marks=1,
                    options=["A", "B", "C", "D"],
                    correct_answer="A",
                )
            )
        if cid in OPEN_CONCEPTS:
            db.merge(
                Question(
                    id=f"Q-{cid}-OPEN",
                    concept_id=cid,
                    type="OPEN_ENDED",
                    text=f"[{cid}] Explain the concept in your own words with one worked example.",
                    max_marks=5,
                    rubric=OPEN_CONCEPTS[cid],
                )
            )
    db.commit()
    return {"students": len(STUDENTS), "concepts": len(CONCEPTS)}


def quiz_answers(run_id: str) -> list[dict]:
    """The submission payload the demo posts to /quiz/submit."""
    payload = []
    for sid, _ in STUDENTS:
        for cid, _name in CONCEPTS:
            correct = MCQ_MATRIX[sid][cid]
            for i in range(1, 6):
                payload.append(
                    {
                        "student_id": sid,
                        "question_id": f"Q-{cid}-{i}",
                        "answer": "A" if i <= correct else "C",
                    }
                )
            if cid in OPEN_CONCEPTS:
                quality = OPEN_QUALITY.get(cid, {}).get(sid, "medium")
                payload.append(
                    {"student_id": sid, "question_id": f"Q-{cid}-OPEN", "answer": ANSWER_TEXT[quality]}
                )
    return payload


def store_answers(db: DBSession, run_id: str, answers: list[dict]) -> int:
    for item in answers:
        db.add(
            StudentAnswer(
                run_id=run_id,
                student_id=item["student_id"],
                question_id=item["question_id"],
                answer=item.get("answer"),
            )
        )
    db.commit()
    return len(answers)


def simulated_evaluation_answers(questions: list[dict], learned: bool = True) -> list[dict]:
    """Answers for the follow-up quiz. ``learned=False`` demonstrates an ineffective session."""
    out = []
    for q in questions:
        if q["type"] == "MCQ":
            options = q.get("options") or []
            raw = (options[0] if learned else options[2]) if options else ("A" if learned else "C")
            answer = raw.split(".")[0].strip()
        elif learned:
            concept = q.get("concept", "the concept")
            answer = (
                f"Definition: {concept} is best described by its underlying mechanism, which I can state "
                f"precisely. Correctness follows from applying that mechanism step by step. There is a boundary "
                f"condition where it stops holding, and here is a fresh example that is different from the one my "
                f"partner used during the session, worked through to the final result."
            )
        else:
            answer = "Not sure, something like what we discussed."
        out.append({"question_id": q["question_id"], "answer": answer})
    return out
