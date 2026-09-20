from __future__ import annotations

import random
from typing import Any

import httpx

from .config import BASE_URL, DEFAULT_CONCEPTS, DEFAULT_QUESTIONS_PER_CONCEPT, DEFAULT_TIMEOUT_SECONDS


class StressClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        response = self.client.request(method, path, json=payload)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        if response.is_error:
            raise RuntimeError(f"{method} {path} failed ({response.status_code}): {body}")
        return body

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/health")

    def create_student(self, student_id: str, name: str, email: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"id": student_id, "name": name, "email": email, "metadata": metadata or {}}
        return self.request("POST", "/api/v1/students", payload)

    def create_concept(self, concept_id: str, name: str, description: str = "") -> dict[str, Any]:
        payload = {"id": concept_id, "name": name, "description": description}
        return self.request("POST", "/api/v1/concepts", payload)

    def create_question(self, question_id: str, concept_id: str, question_type: str, text: str, correct_answer: str | None = None, max_marks: float = 1.0, rubric: str = "") -> dict[str, Any]:
        payload = {
            "id": question_id,
            "concept_id": concept_id,
            "type": question_type,
            "text": text,
            "correct_answer": correct_answer,
            "max_marks": max_marks,
            "rubric": rubric,
        }
        return self.request("POST", "/api/v1/questions", payload)

    def submit_answer(self, question_id: str, student_id: str, answer: str) -> dict[str, Any]:
        payload = {"student_id": student_id, "answer": answer}
        return self.request("POST", f"/api/v1/questions/{question_id}/answers", payload)

    def set_score(self, student_id: str, concept_id: str, score: float, source: str = "manual") -> dict[str, Any]:
        payload = {"concept_id": concept_id, "score": float(score), "source": source}
        return self.request("PUT", f"/api/v1/students/{student_id}/scores", payload)

    def run_profiling(self) -> dict[str, Any]:
        return self.request("POST", "/api/v1/profiling/run")

    def rebuild_graph(self) -> dict[str, Any]:
        return self.request("POST", "/api/v1/graph/rebuild")

    def run_matching(self) -> dict[str, Any]:
        return self.request("POST", "/api/v1/matching/run")

    def approve_all(self, run_id: str, actor: str = "human", duration_minutes: int = 45) -> dict[str, Any]:
        payload = {"actor": actor, "duration_minutes": duration_minutes}
        return self.request("POST", f"/api/v1/matching/runs/{run_id}/approve-all", payload)

    def complete_all_sessions(self, run_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/v1/matching/runs/{run_id}/sessions/complete-all")

    def submit_all_evaluations(self, run_id: str, evaluation_items: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {"evaluations": evaluation_items}
        return self.request("POST", f"/api/v1/matching/runs/{run_id}/evaluations/submit-all", payload)

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/v1/runs/{run_id}")

    def get_analytics(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/analytics")

    def close(self) -> None:
        self.client.close()


def build_concepts() -> list[tuple[str, str, str]]:
    return list(DEFAULT_CONCEPTS)


def build_question_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "Q_REC_01",
            "concept_id": "CON_REC",
            "type": "mcq",
            "text": "Which statement best describes recursion?",
            "correct_answer": "A",
            "max_marks": 1,
            "rubric": "Choice A is the recursive definition.",
        },
        {
            "id": "Q_REC_02",
            "concept_id": "CON_REC",
            "type": "mcq",
            "text": "A recursive function typically ends when it reaches:",
            "correct_answer": "B",
            "max_marks": 1,
            "rubric": "The recursion ends at a base case.",
        },
        {
            "id": "Q_NORM_01",
            "concept_id": "CON_NORM",
            "type": "mcq",
            "text": "Normalisation is best described as:",
            "correct_answer": "B",
            "max_marks": 1,
            "rubric": "Choice B is the best definition.",
        },
        {
            "id": "Q_ARR_01",
            "concept_id": "CON_ARR",
            "type": "mcq",
            "text": "Arrays are usually indexed by:",
            "correct_answer": "C",
            "max_marks": 1,
            "rubric": "Array indexing uses positions.",
        },
        {
            "id": "Q_TREE_01",
            "concept_id": "CON_TREE",
            "type": "mcq",
            "text": "A leaf node in a tree is a node that:",
            "correct_answer": "D",
            "max_marks": 1,
            "rubric": "Leaf nodes have no children.",
        },
    ]


def generate_answer_for_question(question_id: str, student_id: str, question_type: str, correct_answer: str | None) -> str:
    if question_type == "mcq":
        options = ["A", "B", "C", "D"]
        if correct_answer in options:
            return correct_answer
        return random.choice(options)
    prompt_map = {
        "Q_REC_02": f"{student_id} uses a recursive function that reduces the problem size until a base case stops the repetition.",
        "Q_TREE_01": f"{student_id} sees a leaf as a node without children, while a non-leaf node has children and connects the tree structure.",
        "Q_NORM_01": f"{student_id} understands that normalisation brings data into a consistent form for comparison or processing.",
        "Q_ARR_01": f"{student_id} sees that array elements are accessed by index position within a fixed-length sequence.",
    }
    return prompt_map.get(question_id, f"{student_id} answered the question by reasoning through the concept step by step.")
