from collections import defaultdict

from ..config import Settings
from ..db import Store, utcnow
from ..llm import LLMUnavailable, OpenAnswerGrade, OpenRouterClient


class ConceptProfilingAgent:
    """Deterministic scorer for MCQ answers; open answers use a safe local stub in demo mode."""
    def __init__(self, store: Store, settings: Settings):
        self.store = store
        self.llm = OpenRouterClient(settings)
        self.strict_llm = settings.strict_llm

    def score_answer(self, student_id: str, question_id: str, answer: str) -> dict:
        question = self.store.one("SELECT * FROM questions WHERE id=?", (question_id,))
        if not question: raise ValueError("Question not found")
        if not self.store.one("SELECT id FROM students WHERE id=?", (student_id,)): raise ValueError("Student not found")
        if question["type"] == "mcq":
            score = question["max_marks"] if answer.strip().casefold() == (question["correct_answer"] or "").strip().casefold() else 0.0
        else:
            try:
                grade = self.llm.structured(
                    "You are a strict educational assessor. Return only schema-valid JSON. Grade only the supplied answer; do not invent evidence.",
                    f"Question: {question['text']}\nConcept: {question['concept_id']}\nRubric: {question['rubric']}\nMaximum marks: {question['max_marks']}\nStudent answer: {answer}\nReturn score on 0-{question['max_marks']} and normalized_score on 0-1.",
                    OpenAnswerGrade,
                )
                score = min(question["max_marks"], max(0.0, grade.score * question["max_marks"] / 5))
                normalized = round(score / question["max_marks"], 4)
            except LLMUnavailable:
                if self.strict_llm: raise
                # Safe demo/offline fallback; MCQs never reach this branch.
                score = min(question["max_marks"], question["max_marks"] * (0.8 if len(answer.strip()) >= 30 else 0.4))
                normalized = round(score / question["max_marks"], 4)
        if question["type"] == "mcq": normalized = round(score / question["max_marks"], 4)
        with self.store.connection() as conn:
            conn.execute("INSERT INTO answers(student_id,question_id,answer,score,normalized_score) VALUES(?,?,?,?,?) ON CONFLICT(student_id,question_id) DO UPDATE SET answer=excluded.answer,score=excluded.score,normalized_score=excluded.normalized_score", (student_id, question_id, answer, score, normalized))
        return {"student_id": student_id, "question_id": question_id, "score": score, "normalized_score": normalized}

    def build_profiles(self) -> int:
        rows = self.store.all("SELECT a.student_id,q.concept_id,AVG(a.normalized_score) score FROM answers a JOIN questions q ON q.id=a.question_id GROUP BY a.student_id,q.concept_id")
        now = utcnow()
        with self.store.connection() as conn:
            for row in rows:
                conn.execute("INSERT INTO concept_scores(student_id,concept_id,score,source,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(student_id,concept_id) DO UPDATE SET score=excluded.score,source=excluded.source,updated_at=excluded.updated_at", (row["student_id"], row["concept_id"], row["score"], "quiz", now))
        return len(rows)
