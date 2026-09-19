from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .schema import ConceptScore, StudentProfile


def load_question_concepts(path: str | Path) -> dict[str, str]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    mapping = {row["question_id"].strip(): row["concept"].strip() for row in rows}
    if not mapping or any(not key or not value for key, value in mapping.items()):
        raise ValueError("question_concepts.csv contains an empty mapping")
    return mapping


def build_profiles(quiz_path: str | Path, mapping_path: str | Path) -> list[StudentProfile]:
    mapping = load_question_concepts(mapping_path)
    by_student: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    names: dict[str, str] = {}
    with Path(quiz_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"student_id", "student_name", "question_id", "score"}
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"quiz.csv must contain {sorted(required)}")
    for row in rows:
        question_id = row["question_id"].strip()
        if question_id not in mapping:
            raise ValueError(f"No concept mapping for question {question_id}")
        try:
            score = max(0.0, min(1.0, float(row["score"])))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid score for {question_id}") from exc
        student_id = row["student_id"].strip()
        names[student_id] = row["student_name"].strip()
        by_student[student_id][mapping[question_id]].append(score)
    concepts = list(dict.fromkeys(mapping.values()))
    profiles = []
    for student_id in sorted(by_student):
        scores = by_student[student_id]
        if set(scores) != set(concepts):
            raise ValueError(f"Student {student_id} is missing a concept score")
        profiles.append(StudentProfile(
            student_id=student_id,
            student_name=names[student_id],
            concepts=[ConceptScore(concept=c, score=sum(scores[c]) / len(scores[c])) for c in concepts],
        ))
    return profiles


def profile_map(profile: StudentProfile) -> dict[str, float]:
    return {item.concept: item.score for item in profile.concepts}