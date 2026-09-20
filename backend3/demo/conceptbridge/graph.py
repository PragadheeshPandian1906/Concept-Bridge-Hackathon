from collections import Counter, defaultdict

from .config import Settings
from .db import Store, utcnow


class KnowledgeGraph:
    def __init__(self, store: Store, settings: Settings): self.store, self.settings = store, settings

    def rebuild(self) -> int:
        scores = self.store.all("SELECT student_id,concept_id,score FROM concept_scores")
        by_concept: dict[str, list[dict]] = defaultdict(list)
        for score in scores: by_concept[score["concept_id"]].append(score)
        eligible: list[tuple] = []
        for concept_id, values in by_concept.items():
            for teacher in values:
                for learner in values:
                    if teacher["student_id"] == learner["student_id"]: continue
                    gap = teacher["score"] - learner["score"]
                    if teacher["score"] >= self.settings.strength_threshold and learner["score"] < self.settings.gap_threshold and gap >= self.settings.min_transfer_gap:
                        eligible.append((teacher["student_id"], learner["student_id"], concept_id, teacher["score"], learner["score"], gap, gap))
        now = utcnow()
        with self.store.connection() as conn:
            conn.execute("UPDATE edges SET active=0,updated_at=?", (now,))
            for edge in eligible:
                conn.execute("INSERT INTO edges(source_student,target_student,concept_id,teacher_score,learner_score,transfer_gap,edge_score,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source_student,target_student,concept_id) DO UPDATE SET teacher_score=excluded.teacher_score,learner_score=excluded.learner_score,transfer_gap=excluded.transfer_gap,edge_score=excluded.edge_score,active=1,updated_at=excluded.updated_at", (*edge,1,now,now))
        return len(eligible)

    def active_edges(self) -> list[dict]:
        return self.store.all("SELECT e.*,c.name concept,ts.name teacher_name,ls.name learner_name FROM edges e JOIN concepts c ON c.id=e.concept_id JOIN students ts ON ts.id=e.source_student JOIN students ls ON ls.id=e.target_student WHERE e.active=1 ORDER BY e.source_student,e.target_student,e.concept_id")

    def metrics(self) -> dict:
        edges = self.active_edges(); students = self.store.all("SELECT id FROM students")
        pairs = {(e["source_student"],e["target_student"]) for e in edges}
        reciprocal = sum(1 for a,b in pairs if a < b and (b,a) in pairs)
        outgoing = Counter(e["source_student"] for e in edges); connected = {e["source_student"] for e in edges} | {e["target_student"] for e in edges}
        concept_counts = defaultdict(lambda: [0,0])
        for e in edges: concept_counts[e["concept"]][0] += 1; concept_counts[e["concept"]][1] += 1
        # A bottleneck has potential learners but no/one distinct knowledgeable teacher.
        bottlenecks = []
        for concept in self.store.all("SELECT id,name FROM concepts"):
            values = self.store.all("SELECT score FROM concept_scores WHERE concept_id=?", (concept["id"],))
            learners = sum(v["score"] < self.settings.gap_threshold for v in values)
            teachers = sum(v["score"] >= self.settings.strength_threshold for v in values)
            if learners >= 2 and teachers <= 1: bottlenecks.append(concept["name"])
        return {"student_count":len(students),"active_edge_count":len(edges),"reciprocal_pair_count":reciprocal,"isolated_student_ids":[s["id"] for s in students if s["id"] not in connected],"knowledge_hubs":[sid for sid,count in outgoing.items() if count >= 3],"bottleneck_concepts":bottlenecks,"average_transfer_gap":round(sum(e["transfer_gap"] for e in edges)/len(edges),4) if edges else 0}
