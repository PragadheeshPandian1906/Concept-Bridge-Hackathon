from collections import Counter
from itertools import combinations
from uuid import uuid4

from .config import Settings
from .db import Store, utcnow
from .graph import KnowledgeGraph


class MatchmakingAgent:
    """Purely deterministic, exhaustive combination matcher. Reciprocity/cycles only improve score."""
    def __init__(self, store: Store, settings: Settings):
        self.store, self.settings, self.graph = store, settings, KnowledgeGraph(store, settings)

    @staticmethod
    def signature(ids: tuple[str, ...] | list[str]) -> str: return "|".join(sorted(ids))

    def _history(self, signature: str) -> tuple[int, int, float]:
        rows = self.store.all("SELECT outcome,details_json FROM match_history WHERE participants_signature=?", (signature,))
        previous = len(rows); ineffective = sum(row["outcome"] == "INEFFECTIVE" for row in rows)
        gains = []
        for row in rows:
            details = self.store.load(row["details_json"])
            if "average_gain" in details: gains.append(details["average_gain"])
        return previous, ineffective, sum(gains)/len(gains) if gains else 0.0

    def _rejected_signatures(self, root_id: str) -> set[str]:
        rows = self.store.all("SELECT c.participant_signature FROM candidates c JOIN runs r ON r.id=c.run_id WHERE r.root_id=? AND c.status='REJECTED'", (root_id,))
        return {r["participant_signature"] for r in rows}

    def _candidate(self, members: tuple[str, ...], edges: list[dict], concept_count: int) -> dict | None:
        internal = [e for e in edges if e["source_student"] in members and e["target_student"] in members]
        # This is the only relationship-validity rule: a group must transfer at least one real concept.
        if not internal: return None
        outgoing = Counter(e["source_student"] for e in internal)
        historic_load = {student: self.store.one("SELECT COUNT(*) count FROM learning_gains WHERE teacher_id=?", (student,))["count"] for student in members}
        if any(historic_load[s] + outgoing[s] > self.settings.max_teaching_load for s in outgoing): return None
        concepts = sorted({e["concept_id"] for e in internal})
        coverage = len(concepts) / max(concept_count, 1)
        pairs = {(e["source_student"],e["target_student"]) for e in internal}
        reciprocal = sum(1 for a,b in pairs if a < b and (b,a) in pairs)
        reciprocity = reciprocal / max(len(pairs), 1)
        # Cycle is evidence only; a source fan-out remains a valid group.
        cycle = any(a == e2["target_student"] and b == e2["source_student"] for a,b in pairs for e2 in internal)
        transfer_strength = sum(e["transfer_gap"] for e in internal) / len(internal)
        balance = 1 - (max(outgoing.values()) - min(outgoing.values())) / max(len(internal), 1)
        fairness = max(0.0, min(1.0, balance))
        signature = self.signature(members); previous, ineffective, observed_gain = self._history(signature)
        observed_effectiveness = max(0.0, min(1.0, observed_gain))
        penalty = previous*self.settings.previous_match_penalty + ineffective*self.settings.ineffective_match_penalty
        raw = (self.settings.weight_coverage*coverage + self.settings.weight_reciprocity*reciprocity + self.settings.weight_transfer_strength*transfer_strength + self.settings.weight_fairness*fairness + self.settings.weight_effectiveness*observed_effectiveness - penalty)
        relationships = [{"teacher_id":e["source_student"],"teacher_name":e["teacher_name"],"learner_id":e["target_student"],"learner_name":e["learner_name"],"concept_id":e["concept_id"],"concept":e["concept"],"teacher_score":round(e["teacher_score"],3),"learner_score":round(e["learner_score"],3),"transfer_gap":round(e["transfer_gap"],3)} for e in internal]
        evidence = {"knowledge_coverage":round(coverage,4),"knowledge_coverage_percent":round(coverage*100,2),"reciprocity":round(reciprocity,4),"knowledge_cycle":cycle,"transfer_strength":round(transfer_strength,4),"fairness":round(fairness,4),"previous_match_penalty":round(previous*self.settings.previous_match_penalty,4),"ineffective_match_penalty":round(ineffective*self.settings.ineffective_match_penalty,4),"observed_effectiveness":round(observed_effectiveness,4),"teaching_load":dict(outgoing),"reasons":[f"{r['teacher_name']} is strong in {r['concept']} ({r['teacher_score']:.2f}) while {r['learner_name']} has a gap ({r['learner_score']:.2f}); transfer gap {r['transfer_gap']:.2f}." for r in relationships] + [f"The group covers {len(concepts)} relevant concept(s).", "Reciprocity and cycles affect ranking only; they are not validity requirements."]}
        return {"participant_ids":list(members),"signature":signature,"relationships":relationships,"evidence":evidence,"score":round(max(0.0, raw),4)}

    def generate(self, root_id: str, include_rejected: bool = False) -> tuple[list[dict], dict]:
        students = [s["id"] for s in self.store.all("SELECT id FROM students ORDER BY id")]; edges = self.graph.active_edges()
        concepts = self.store.all("SELECT id FROM concepts"); considered = {}
        candidates = []
        for size in range(self.settings.min_group_size, min(self.settings.max_group_size,len(students))+1):
            considered[str(size)] = 0
            for members in combinations(students,size):
                considered[str(size)] += 1
                candidate = self._candidate(members,edges,len(concepts))
                if candidate: candidates.append(candidate)
        rejected = self._rejected_signatures(root_id)
        filtered = [c for c in candidates if include_rejected or c["signature"] not in rejected]
        # Reintroduce candidates only when excluding rejections would leave the human no options.
        final = filtered if filtered else candidates
        final.sort(key=lambda c:(-c["score"],c["signature"]))
        return final,{"combinations_considered":considered,"all_valid_before_rematch_filter":len(candidates),"rejected_excluded":len(candidates)-len(filtered)}

    def persist_candidates(self, run_id: str, candidates: list[dict]) -> list[dict]:
        now=utcnow()
        with self.store.connection() as conn:
            for candidate in candidates:
                candidate["id"] = f"CAN-{uuid4().hex[:12]}"; candidate["run_id"] = run_id; candidate["status"]="PENDING"
                conn.execute("INSERT INTO candidates(id,run_id,participant_ids_json,participant_signature,relationships_json,evidence_json,score,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (candidate["id"],run_id,self.store.dump(candidate["participant_ids"]),candidate["signature"],self.store.dump(candidate["relationships"]),self.store.dump(candidate["evidence"]),candidate["score"],"PENDING",now))
        return candidates
