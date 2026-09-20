import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import Settings, get_settings


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS concepts (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS concept_scores (student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE, concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE, score REAL NOT NULL CHECK(score >= 0 AND score <= 1), source TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(student_id, concept_id));
CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, concept_id TEXT NOT NULL REFERENCES concepts(id), type TEXT NOT NULL CHECK(type IN ('mcq','open')), text TEXT NOT NULL, correct_answer TEXT, max_marks REAL NOT NULL DEFAULT 1, rubric TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(id), question_id TEXT NOT NULL REFERENCES questions(id), answer TEXT NOT NULL, score REAL, normalized_score REAL, UNIQUE(student_id, question_id));
CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY AUTOINCREMENT, source_student TEXT NOT NULL REFERENCES students(id), target_student TEXT NOT NULL REFERENCES students(id), concept_id TEXT NOT NULL REFERENCES concepts(id), teacher_score REAL NOT NULL, learner_score REAL NOT NULL, transfer_gap REAL NOT NULL, edge_score REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(source_student,target_student,concept_id));
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, root_id TEXT NOT NULL, parent_run_id TEXT REFERENCES runs(id), iteration INTEGER NOT NULL, current_state TEXT NOT NULL, previous_state TEXT, trigger TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transitions (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, from_state TEXT, to_state TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, participant_ids_json TEXT NOT NULL, participant_signature TEXT NOT NULL, relationships_json TEXT NOT NULL, evidence_json TEXT NOT NULL, score REAL NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_candidates_run ON candidates(run_id);
CREATE TABLE IF NOT EXISTS candidate_decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL REFERENCES candidates(id), action TEXT NOT NULL CHECK(action IN ('APPROVED','REJECTED')), actor TEXT NOT NULL, reason TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL UNIQUE REFERENCES candidates(id), run_id TEXT NOT NULL REFERENCES runs(id), status TEXT NOT NULL, plan_json TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT);
CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id), status TEXT NOT NULL, questions_json TEXT NOT NULL, result_json TEXT, created_at TEXT NOT NULL, submitted_at TEXT);
CREATE TABLE IF NOT EXISTS learning_gains (id INTEGER PRIMARY KEY AUTOINCREMENT, evaluation_id TEXT NOT NULL REFERENCES evaluations(id), teacher_id TEXT NOT NULL, learner_id TEXT NOT NULL, concept_id TEXT NOT NULL, pre_score REAL NOT NULL, post_score REAL NOT NULL, gain REAL NOT NULL, effective INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS match_history (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL REFERENCES candidates(id), participants_signature TEXT NOT NULL, outcome TEXT NOT NULL, created_at TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS idx_history_signature ON match_history(participants_signature);
"""


class Store:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings(); self.settings.ensure_directories(); self.path = self.settings.database_path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path); conn.row_factory = sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn; conn.commit()
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn: conn.executescript(SCHEMA)
    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone(); return dict(row) if row else None
    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn: return [dict(row) for row in conn.execute(sql, params).fetchall()]
    @staticmethod
    def dump(value: Any) -> str: return json.dumps(value, separators=(",", ":"), sort_keys=True)
    @staticmethod
    def load(value: str) -> Any: return json.loads(value)
