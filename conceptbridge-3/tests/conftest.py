import os
import tempfile
from pathlib import Path

os.environ["DEMO_MODE"] = "true"
os.environ.pop("OPENROUTER_API_KEY", None)
_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp/'test.db'}"
os.environ["ARTIFACTS_DIR"] = str(_tmp / "artifacts")

import pytest  # noqa: E402

from demo.conceptbridge.persistence.database import SessionLocal, reset_db  # noqa: E402
from demo.conceptbridge.seed import demo_data  # noqa: E402
from demo.conceptbridge.state import create_run  # noqa: E402


@pytest.fixture()
def db():
    reset_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded(db):
    demo_data.seed(db)
    run = create_run(db)
    demo_data.store_answers(db, run.run_id, demo_data.quiz_answers(run.run_id))
    return db, run.run_id
