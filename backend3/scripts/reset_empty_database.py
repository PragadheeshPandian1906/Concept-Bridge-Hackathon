"""Delete all ConceptBridge records while preserving the SQLite schema."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.conceptbridge.db import Store


# Children must be deleted before rows they reference.
TABLES_IN_DELETE_ORDER = [
    "learning_gains", "evaluations", "sessions", "candidate_decisions",
    "match_history", "candidates", "transitions", "runs", "edges",
    "answers", "questions", "concept_scores", "concepts", "students",
]


def main() -> None:
    store = Store()
    store.initialize()
    with store.connection() as connection:
        for table in TABLES_IN_DELETE_ORDER:
            connection.execute(f"DELETE FROM {table}")
    print("ConceptBridge database cleared. Schema remains intact; no demo data was seeded.")


if __name__ == "__main__":
    main()
