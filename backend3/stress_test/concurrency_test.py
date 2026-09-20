from __future__ import annotations

import concurrent.futures
import time
from typing import Any

from .seed_data import StressClient, build_question_specs, generate_answer_for_question


def run_concurrency_test(base_url: str, workers: int = 10, students_per_worker: int = 2) -> dict[str, Any]:
    client = StressClient(base_url)
    started = time.time()
    question_specs = build_question_specs()
    results: list[dict[str, Any]] = []

    try:
        client.health()

        def worker(index: int) -> dict[str, Any]:
            local = StressClient(base_url)
            start = time.time()
            for student_offset in range(students_per_worker):
                student_id = f"C{index:02d}_{student_offset:02d}"
                local.create_student(student_id, f"Concurrent {index} {student_offset}", f"c{index}_{student_offset}@example.com")
                for q in question_specs:
                    answer = generate_answer_for_question(q["id"], student_id, q["type"], q["correct_answer"])
                    local.submit_answer(q["id"], student_id, answer)
            duration = round(time.time() - start, 3)
            return {"worker": index, "duration_seconds": duration, "students": students_per_worker}

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, idx) for idx in range(workers)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        return {
            "workers": workers,
            "students_created": sum(r["students"] for r in results),
            "execution_seconds": round(time.time() - started, 3),
            "details": results,
        }
    finally:
        client.close()
