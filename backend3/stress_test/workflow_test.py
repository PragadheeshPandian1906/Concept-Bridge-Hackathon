from __future__ import annotations

import time
from typing import Any

from .seed_data import StressClient, build_concepts, build_question_specs, generate_answer_for_question


def seed_and_run_workflow(base_url: str, students: int, concepts: list[tuple[str, str, str]] | None = None, questions_per_concept: int = 3, answers_per_student: int = 3) -> dict[str, Any]:
    client = StressClient(base_url)
    start = time.time()
    metrics: dict[str, Any] = {"seed": {}, "flow": {}}

    try:
        client.health()
        concept_list = concepts or build_concepts()
        for concept_id, name, description in concept_list:
            client.create_concept(concept_id, name, description)
        metrics["seed"]["concepts_created"] = len(concept_list)

        for idx in range(1, students + 1):
            student_id = f"S{idx:03d}"
            client.create_student(student_id, f"Student {idx}", f"student{idx}@example.com", {"group": "stress-test"})
        metrics["seed"]["students_created"] = students

        question_specs = build_question_specs()
        for q in question_specs:
            client.create_question(
                q["id"],
                q["concept_id"],
                q["type"],
                q["text"],
                q["correct_answer"],
                q["max_marks"],
                q["rubric"],
            )
        metrics["seed"]["questions_created"] = len(question_specs)

        for idx in range(1, students + 1):
            student_id = f"S{idx:03d}"
            for q in question_specs[:answers_per_student]:
                answer = generate_answer_for_question(q["id"], student_id, q["type"], q["correct_answer"])
                if q["type"] == "mcq":
                    # Create realistic variation so students differ in skill instead of all being identical.
                    answer = ["A", "B", "C", "D"][((idx + hash(q["id"]) % 10) % 4)]
                client.submit_answer(q["id"], student_id, answer)
        metrics["seed"]["answers_submitted"] = students * min(len(question_specs), answers_per_student)

        concept_ids = [concept_id for concept_id, _, _ in concept_list]
        for idx in range(1, students + 1):
            student_id = f"S{idx:03d}"
            for concept_index, concept_id in enumerate(concept_ids):
                score = max(0.05, min(0.95, round((idx % 5) * 0.12 + ((concept_index + 1) * 0.08) + ((idx % 3) * 0.05), 2)))
                if idx % 2 == 0:
                    score = max(0.15, score - 0.12)
                client.set_score(student_id, concept_id, score, source="stress_seed")

        profiling_result = client.run_profiling()
        metrics["flow"]["profiling"] = profiling_result

        graph_result = client.rebuild_graph()
        metrics["flow"]["graph"] = graph_result

        matching_result = client.run_matching()
        run_id = matching_result.get("run", {}).get("id") or matching_result.get("id")
        if not run_id:
            raise RuntimeError(f"Matching response did not include a run id: {matching_result}")
        candidate_count = matching_result.get("candidate_count") or len(matching_result.get("candidates", []))
        metrics["flow"]["matching"] = {"run_id": run_id, "candidate_count": candidate_count}

        if candidate_count == 0:
            raise RuntimeError(f"No valid candidates were generated for run {run_id}; cannot continue workflow.")

        approve_result = client.approve_all(run_id)
        metrics["flow"]["approve_all"] = approve_result

        complete_result = client.complete_all_sessions(run_id)
        metrics["flow"]["complete_all_sessions"] = complete_result

        evaluations = complete_result.get("evaluations", [])
        evaluation_items = []
        for ev in evaluations:
            post_scores = {}
            for q in ev.get("questions", []):
                concept_id = q["concept_id"]
                post_scores[concept_id] = 1.0
            evaluation_items.append({"evaluation_id": ev["id"], "post_scores": post_scores})

        submit_result = client.submit_all_evaluations(run_id, evaluation_items)
        metrics["flow"]["submit_all_evaluations"] = submit_result

        metrics["total_seconds"] = round(time.time() - start, 3)
        return metrics
    finally:
        client.close()
