"""Deterministic evaluation questions for DEMO_MODE."""
from __future__ import annotations


def stub_questions(concepts: list[dict], per_concept: int = 3) -> dict:
    questions = []
    for item in concepts:
        cid, name = item["concept_id"], item["concept"]
        for i in range(max(1, per_concept - 1)):
            questions.append(
                {
                    "question_id": f"EV-{cid}-M{i+1}",
                    "concept": name,
                    "type": "MCQ",
                    "text": f"In a new scenario involving {name}, which statement is correct? (variant {i+1})",
                    "options": [
                        f"A. A correct application of {name}",
                        f"B. A common misconception about {name}",
                        f"C. An unrelated claim",
                        f"D. A partially correct but incomplete claim",
                    ],
                    "correct_answer": "A",
                    "max_marks": 1,
                }
            )
        questions.append(
            {
                "question_id": f"EV-{cid}-O1",
                "concept": name,
                "type": "OPEN_ENDED",
                "text": f"Explain {name} in your own words and describe one case where it does not apply.",
                "rubric": f"definition mechanism correctness boundary condition example {name}",
                "max_marks": 5,
            }
        )
    return {"questions": questions}
