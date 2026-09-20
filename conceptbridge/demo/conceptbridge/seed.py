from .db import Store, utcnow


DEMO_CONCEPTS = [
    ("recursion", "Recursion"), ("arrays", "Arrays"), ("trees", "Trees"), ("sql_joins", "SQL Joins"),
    ("normalization", "Normalization"), ("transactions", "Transactions"), ("operating_systems", "Operating Systems"), ("networking", "Networking"),
]
DEMO_SCORES = {
    "S001": [0.92,0.62,0.72,0.32,0.35,0.40,0.52,0.45], "S002": [0.32,0.78,0.42,0.91,0.45,0.48,0.50,0.38],
    "S003": [0.48,0.45,0.90,0.42,0.86,0.36,0.48,0.50], "S004": [0.84,0.40,0.35,0.44,0.38,0.91,0.45,0.72],
    "S005": [0.38,0.86,0.43,0.76,0.41,0.35,0.82,0.44], "S006": [0.44,0.36,0.83,0.31,0.72,0.42,0.43,0.88],
    "S007": [0.78,0.52,0.47,0.81,0.39,0.74,0.40,0.35], "S008": [0.29,0.31,0.34,0.37,0.32,0.35,0.31,0.30],
}


def seed_demo(store: Store, reset: bool = False) -> None:
    store.initialize(); now=utcnow()
    with store.connection() as conn:
        if reset:
            # Delete dependent historical rows before their candidate/run parents.
            for table in ["learning_gains","evaluations","sessions","candidate_decisions","match_history","candidates","transitions","runs","edges","answers","questions","concept_scores","concepts","students"]:
                conn.execute(f"DELETE FROM {table}")
        for concept_id,name in DEMO_CONCEPTS: conn.execute("INSERT OR IGNORE INTO concepts(id,name,description) VALUES(?,?,?)",(concept_id,name,f"Demo {name} concept"))
        for student_id,scores in DEMO_SCORES.items():
            conn.execute("INSERT OR IGNORE INTO students(id,name,email,metadata_json,created_at) VALUES(?,?,?,?,?)",(student_id,f"Student {student_id[-1]}",f"{student_id.lower()}@example.test","{}",now))
            for (concept_id,_),score in zip(DEMO_CONCEPTS,scores): conn.execute("INSERT INTO concept_scores(student_id,concept_id,score,source,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(student_id,concept_id) DO UPDATE SET score=excluded.score,source=excluded.source,updated_at=excluded.updated_at",(student_id,concept_id,score,"demo",now))
