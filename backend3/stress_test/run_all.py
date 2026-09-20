from __future__ import annotations

import json
from pathlib import Path

from .concurrency_test import run_concurrency_test
from .workflow_test import seed_and_run_workflow


def main() -> None:
    base_url = "http://127.0.0.1:8000"
    workflow = seed_and_run_workflow(base_url, students=10)
    concurrency = run_concurrency_test(base_url, workers=5, students_per_worker=2)

    report = {
        "workflow": workflow,
        "concurrency": concurrency,
    }

    output_path = Path(__file__).resolve().parent / "stress_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
