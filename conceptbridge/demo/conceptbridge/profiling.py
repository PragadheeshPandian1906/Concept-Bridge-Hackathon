"""PROFILING - deterministic concept-level proficiency.

Question-level evidence in, concept-level profiles out. No model is
involved: numbers are computed by Python and an LLM can never override
them.

    concept_score = sum(question_scores_for_concept)
                    / number_of_questions_for_concept      clamped to [0, 1]

Free-text student responses are carried along as *data* only. They are
never interpreted as instructions and never affect a score.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .schema import ConceptScore, StudentProfile

DATA_DIR = Path(__file__).resolve().parent / "data"
QUIZ_CSV = DATA_DIR / "quiz.csv"
CONCEPT_MAP_CSV = DATA_DIR / "question_concepts.csv"


class ProfilingError(ValueError):
    """Input data is missing, malformed or unmapped."""


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


# ------------------------------------------------------------- loading
def load_concept_map(path: str | Path = CONCEPT_MAP_CSV) -> dict[str, str]:
    path = Path(path)
    if not path.exists():
        raise ProfilingError(f"concept map not found: {path}")
    mapping: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            qid = (row.get("question_id") or "").strip()
            concept = (row.get("concept") or "").strip()
            if not qid or not concept:
                raise ProfilingError(f"invalid concept-map row: {row}")
            mapping[qid] = concept
    if not mapping:
        raise ProfilingError("concept map is empty")
    return mapping


def load_quiz(path: str | Path = QUIZ_CSV) -> list[dict]:
    path = Path(path)
    if not path.exists():
        raise ProfilingError(f"quiz file not found: {path}")
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for line_no, row in enumerate(csv.DictReader(handle), start=2):
            sid = (row.get("student_id") or "").strip()
            qid = (row.get("question_id") or "").strip()
            raw = (row.get("score") or "").strip()
            if not sid or not qid:
                raise ProfilingError(f"quiz.csv line {line_no}: missing student or question id")
            try:
                score = float(raw)
            except ValueError:
                raise ProfilingError(f"quiz.csv line {line_no}: non-numeric score {raw!r}")
            rows.append({
                "student_id": sid,
                "student_name": (row.get("student_name") or sid).strip(),
                "question_id": qid,
                "score": clamp(score),
                # untrusted free text - kept for the record, never parsed
                "response_text": row.get("response_text") or "",
            })
    if not rows:
        raise ProfilingError("quiz.csv contains no rows")
    return rows


# ------------------------------------------------------------ profiling
def build_profiles(
    quiz_rows: list[dict],
    concept_map: dict[str, str],
    students: list[str] | None = None,
) -> list[StudentProfile]:
    """Aggregate question evidence into one profile per student."""
    unmapped = sorted({r["question_id"] for r in quiz_rows} - set(concept_map))
    if unmapped:
        raise ProfilingError(f"questions with no concept mapping: {unmapped}")

    concepts = sorted(set(concept_map.values()))
    names: dict[str, str] = {}
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for row in quiz_rows:
        sid = row["student_id"]
        names.setdefault(sid, row["student_name"])
        buckets[sid][concept_map[row["question_id"]]].append(row["score"])

    wanted = None
    if students:
        wanted = {s.strip().lower() for s in students}

    profiles: list[StudentProfile] = []
    for sid in sorted(buckets):
        name = names[sid]
        if wanted and sid.lower() not in wanted and name.lower() not in wanted:
            continue
        scores = []
        for concept in concepts:
            values = buckets[sid].get(concept)
            if not values:
                raise ProfilingError(
                    f"student {sid} has no evidence for concept {concept!r}"
                )
            scores.append(ConceptScore(
                concept=concept,
                score=clamp(round(sum(values) / len(values), 4)),
            ))
        profiles.append(StudentProfile(student_id=sid, student_name=name, concepts=scores))

    if not profiles:
        raise ProfilingError("no student profiles were produced")
    return profiles


def profile_students(
    quiz_path: str | Path = QUIZ_CSV,
    concept_map_path: str | Path = CONCEPT_MAP_CSV,
    students: list[str] | None = None,
) -> list[StudentProfile]:
    """Convenience: load both CSVs and return profiles."""
    return build_profiles(load_quiz(quiz_path), load_concept_map(concept_map_path), students)


def concept_list(profiles: list[StudentProfile]) -> list[str]:
    return [c.concept for c in profiles[0].concepts] if profiles else []
