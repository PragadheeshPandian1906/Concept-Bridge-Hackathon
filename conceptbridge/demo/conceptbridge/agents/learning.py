from uuid import uuid4
from ..config import Settings
from ..db import Store, utcnow
from ..llm import FollowUpQuestionSet, LLMUnavailable, OpenRouterClient, SessionPlanContent


class PeerLearningAgent:
    """Produces a structured deterministic fallback plan when no LLM is configured."""
    def __init__(self, store: Store, settings: Settings):
        self.store = store
        self.llm = OpenRouterClient(settings)
    def create_session(self, candidate: dict, duration_minutes: int) -> dict:
        relationships = self.store.load(candidate["relationships_json"])
        fallback_rounds = [{"teacher": r["teacher_id"], "learner": r["learner_id"], "concept": r["concept"], "objective": f"Close the {r['concept']} gap of {r['transfer_gap']:.2f}", "explanation": f"{r['teacher_name']} explains {r['concept']} with a worked example.", "activity": f"{r['learner_name']} solves a fresh {r['concept']} exercise.", "understanding_check": f"Explain the key {r['concept']} idea in your own words."} for r in relationships]
        allowed = {(r["teacher_id"], r["learner_id"], r["concept_id"]): r for r in relationships}
        try:
            generated = self.llm.structured(
                "You design concise peer-learning sessions. You must preserve every supplied teacher, learner, and concept exactly. Return only schema-valid JSON.",
                f"Duration minutes: {duration_minutes}\nTransfer relationships (the fixed source of truth): {self.store.dump(relationships)}\nCreate one practical round for each relationship with an objective, explanation, example, activity, and understanding check.",
                SessionPlanContent,
            )
            received = {(round_.teacher_id, round_.learner_id, round_.concept_id) for round_ in generated.rounds}
            if received != set(allowed): raise LLMUnavailable("LLM changed the fixed transfer relationships")
            rounds = [{"teacher": r.teacher_id,"learner":r.learner_id,"concept":allowed[(r.teacher_id,r.learner_id,r.concept_id)]["concept"],"objective":r.objective,"explanation":r.explanation,"example":r.example,"activity":r.activity,"understanding_check":r.understanding_check} for r in generated.rounds]
            plan = {"duration_minutes":duration_minutes,"overall_objective":generated.overall_objective,"rounds":rounds,"source":"openrouter"}
        except LLMUnavailable:
            plan = {"duration_minutes": duration_minutes, "rounds": fallback_rounds, "source": "deterministic_fallback"}
        session_id = f"SES-{uuid4().hex[:12]}"
        with self.store.connection() as conn:
            conn.execute("INSERT INTO sessions(id,candidate_id,run_id,status,plan_json,created_at) VALUES(?,?,?,?,?,?)", (session_id,candidate["id"],candidate["run_id"],"PLANNED",self.store.dump(plan),utcnow()))
        return {"id": session_id, "status": "PLANNED", "plan": plan}

    def complete(self, session_id: str) -> None:
        with self.store.connection() as conn: conn.execute("UPDATE sessions SET status='COMPLETED',completed_at=? WHERE id=?", (utcnow(),session_id))


class EvaluationAgent:
    def __init__(self, store: Store, settings: Settings):
        self.store = store
        self.llm = OpenRouterClient(settings)
    def create(self, session_id: str) -> dict:
        session = self.store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
        if not session: raise ValueError("Session not found")
        candidate = self.store.one("SELECT * FROM candidates WHERE id=?", (session["candidate_id"],))
        relationships = self.store.load(candidate["relationships_json"])
        concepts = {r["concept_id"]: r["concept"] for r in relationships}
        fallback = [{"concept_id": concept_id, "prompt": f"Apply {concept} to a new problem; do not repeat the session example.", "type":"open", "rubric":"Demonstrates accurate application of the concept."} for concept_id,concept in concepts.items()]
        try:
            generated = self.llm.structured(
                "You create fair follow-up assessments. Questions must test transfer, not repeat examples. Use only the supplied concept IDs and return schema-valid JSON.",
                f"Session transfer relationships: {self.store.dump(relationships)}\nCreate one open-ended follow-up question for every distinct taught concept.",
                FollowUpQuestionSet,
            )
            if {question.concept_id for question in generated.questions} != set(concepts): raise LLMUnavailable("LLM omitted or changed taught concepts")
            questions = [question.model_dump() for question in generated.questions]
            source = "openrouter"
        except LLMUnavailable:
            questions = fallback; source = "deterministic_fallback"
        evaluation_id = f"EVAL-{uuid4().hex[:12]}"
        with self.store.connection() as conn:
            conn.execute("INSERT INTO evaluations(id,session_id,status,questions_json,created_at) VALUES(?,?,?,?,?)", (evaluation_id,session_id,"PENDING",self.store.dump(questions),utcnow()))
        return {"id": evaluation_id,"session_id":session_id,"status":"PENDING","questions":questions,"source":source}
