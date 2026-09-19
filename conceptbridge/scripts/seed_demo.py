"""Seed students, concepts, questions and quiz answers into the database."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.conceptbridge.persistence.database import SessionLocal, init_db  # noqa: E402
from demo.conceptbridge.seed import demo_data  # noqa: E402
from demo.conceptbridge.state import create_run  # noqa: E402

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    print(demo_data.seed(db))
    run = create_run(db)
    demo_data.store_answers(db, run.run_id, demo_data.quiz_answers(run.run_id))
    print(f"seeded. run_id = {run.run_id}")
    db.close()
