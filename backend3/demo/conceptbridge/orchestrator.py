from uuid import uuid4

from .agents.learning import EvaluationAgent, PeerLearningAgent
from .config import Settings
from .db import Store, utcnow
from .graph import KnowledgeGraph
from .matching import MatchmakingAgent


class Orchestrator:
    def __init__(self, store: Store, settings: Settings):
        self.store, self.settings = store, settings
        self.graph = KnowledgeGraph(store, settings); self.matcher = MatchmakingAgent(store, settings)
        self.learning = PeerLearningAgent(store, settings); self.evaluation = EvaluationAgent(store, settings)

    def transition(self, run_id: str, state: str, reason: str) -> None:
        run = self.store.one("SELECT current_state FROM runs WHERE id=?", (run_id,))
        if not run: raise ValueError("Run not found")
        allowed = {"INPUT":{"PROFILING","MATCHING"},"PROFILING":{"MATCHING"},"MATCHING":{"WAITING_FOR_HUMAN_REVIEW","NO_MATCH_FOUND"},"WAITING_FOR_HUMAN_REVIEW":{"SESSION","MATCHING"},"SESSION":{"EVALUATION"},"EVALUATION":{"UPDATED_PROFILE","MATCHING"},"UPDATED_PROFILE":{"FINISHED"},"NO_MATCH_FOUND":{"FINISHED"}}
        if state not in allowed.get(run["current_state"],set()): raise ValueError(f"Invalid transition {run['current_state']} -> {state}")
        now=utcnow()
        with self.store.connection() as conn:
            conn.execute("UPDATE runs SET previous_state=?,current_state=?,updated_at=? WHERE id=?", (run["current_state"],state,now,run_id))
            conn.execute("INSERT INTO transitions(run_id,from_state,to_state,reason,created_at) VALUES(?,?,?,?,?)", (run_id,run["current_state"],state,reason,now))

    def run_matching(self, trigger: str = "manual", parent_run_id: str | None = None) -> dict:
        self.graph.rebuild()
        parent = self.store.one("SELECT * FROM runs WHERE id=?",(parent_run_id,)) if parent_run_id else None
        run_id=f"RUN-{uuid4().hex[:12]}"; root_id=parent["root_id"] if parent else run_id; iteration=(parent["iteration"]+1) if parent else 1; now=utcnow()
        with self.store.connection() as conn:
            conn.execute("INSERT INTO runs(id,root_id,parent_run_id,iteration,current_state,previous_state,trigger,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(run_id,root_id,parent_run_id,iteration,"INPUT",None,trigger,now,now))
            conn.execute("INSERT INTO transitions(run_id,from_state,to_state,reason,created_at) VALUES(?,?,?,?,?)",(run_id,None,"INPUT","run created",now))
        self.transition(run_id,"PROFILING","profiles available")
        self.transition(run_id,"MATCHING",trigger)
        candidates, stats=self.matcher.generate(root_id)
        if not candidates:
            self.transition(run_id,"NO_MATCH_FOUND","no valid group has an internal transfer edge")
            return self.run_view(run_id)|{"candidate_count":0,"candidates":[],"generation":stats}
        candidates=self.matcher.persist_candidates(run_id,candidates)
        self.transition(run_id,"WAITING_FOR_HUMAN_REVIEW","all valid candidates generated")
        return self.run_view(run_id)|{"candidate_count":len(candidates),"candidates":candidates,"generation":stats}

    def candidate(self,candidate_id:str)->dict:
        row=self.store.one("SELECT * FROM candidates WHERE id=?",(candidate_id,))
        if not row: raise ValueError("Candidate not found")
        return {**row,"participant_ids":self.store.load(row.pop("participant_ids_json")),"relationships":self.store.load(row.pop("relationships_json")),"evidence":self.store.load(row.pop("evidence_json"))}

    def approve(self,candidate_id:str,actor:str,duration:int)->dict:
        candidate=self.candidate(candidate_id); run=self.store.one("SELECT * FROM runs WHERE id=?",(candidate["run_id"],))
        if candidate["status"]!="PENDING" or run["current_state"]!="WAITING_FOR_HUMAN_REVIEW": raise ValueError("Candidate is not awaiting human review")
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/orchestrator.py
=======
        # Fail closed before changing approval state when strict LLM generation is unavailable.
        plan = self.learning.generate_plan(candidate, duration)
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/orchestrator.py
        now=utcnow()
        with self.store.connection() as conn:
            conn.execute("UPDATE candidates SET status='APPROVED' WHERE id=?",(candidate_id,)); conn.execute("INSERT INTO candidate_decisions(candidate_id,action,actor,reason,created_at) VALUES(?,?,?,?,?)",(candidate_id,"APPROVED",actor,None,now)); conn.execute("INSERT INTO match_history(candidate_id,participants_signature,outcome,created_at) VALUES(?,?,?,?)",(candidate_id,candidate["participant_signature"],"APPROVED",now))
        self.transition(candidate["run_id"],"SESSION","human approved candidate")
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/orchestrator.py
        return {"candidate":self.candidate(candidate_id),"session":self.learning.create_session(candidate,duration),"run":self.run_view(candidate["run_id"])}
=======
        return {"candidate":self.candidate(candidate_id),"session":self.learning.create_session(candidate,duration,plan),"run":self.run_view(candidate["run_id"])}
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/orchestrator.py

    def approve_all(self, run_id: str, actor: str, duration: int) -> dict:
        """Human batch decision: approve every still-pending candidate in this exact run."""
        run = self.store.one("SELECT * FROM runs WHERE id=?", (run_id,))
        if not run: raise ValueError("Run not found")
        if run["current_state"] != "WAITING_FOR_HUMAN_REVIEW":
            raise ValueError("Run is not awaiting human review")
        candidate_ids = [row["id"] for row in self.store.all("SELECT id FROM candidates WHERE run_id=? AND status='PENDING' ORDER BY score DESC,id", (run_id,))]
        if not candidate_ids: raise ValueError("Run has no pending candidates")
        candidates = [self.candidate(candidate_id) for candidate_id in candidate_ids]
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/orchestrator.py
=======
        # Generate all plans before persisting the batch decision, preventing partial batches.
        plans = {candidate["id"]: self.learning.generate_plan(candidate, duration) for candidate in candidates}
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/orchestrator.py
        now = utcnow()
        with self.store.connection() as conn:
            for candidate in candidates:
                conn.execute("UPDATE candidates SET status='APPROVED' WHERE id=?", (candidate["id"],))
                conn.execute("INSERT INTO candidate_decisions(candidate_id,action,actor,reason,created_at) VALUES(?,?,?,?,?)", (candidate["id"],"APPROVED",actor,"batch approval",now))
                conn.execute("INSERT INTO match_history(candidate_id,participants_signature,outcome,created_at) VALUES(?,?,?,?)", (candidate["id"],candidate["participant_signature"],"APPROVED",now))
        self.transition(run_id,"SESSION","human approved all pending candidates")
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/orchestrator.py
        sessions = [self.learning.create_session(candidate,duration) for candidate in candidates]
=======
        sessions = [self.learning.create_session(candidate,duration,plans[candidate["id"]]) for candidate in candidates]
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/orchestrator.py
        return {"run":self.run_view(run_id),"approved_count":len(candidates),"candidate_ids":candidate_ids,"sessions":sessions}

    def reject(self,candidate_id:str,actor:str,reason:str|None)->dict:
        candidate=self.candidate(candidate_id); run=self.store.one("SELECT * FROM runs WHERE id=?",(candidate["run_id"],))
        if candidate["status"]!="PENDING" or run["current_state"]!="WAITING_FOR_HUMAN_REVIEW": raise ValueError("Candidate is not awaiting human review")
        now=utcnow()
        with self.store.connection() as conn:
            conn.execute("UPDATE candidates SET status='REJECTED' WHERE id=?",(candidate_id,)); conn.execute("INSERT INTO candidate_decisions(candidate_id,action,actor,reason,created_at) VALUES(?,?,?,?,?)",(candidate_id,"REJECTED",actor,reason,now)); conn.execute("INSERT INTO match_history(candidate_id,participants_signature,outcome,created_at,details_json) VALUES(?,?,?,?,?)",(candidate_id,candidate["participant_signature"],"REJECTED",now,self.store.dump({"reason":reason})))
        self.transition(candidate["run_id"],"MATCHING","human rejected candidate")
        return self.run_matching("human rejection",candidate["run_id"])

    def start_evaluation(self, session_id: str) -> dict:
        session = self.store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
        if not session: raise ValueError("Session not found")
        run = self.store.one("SELECT current_state FROM runs WHERE id=?", (session["run_id"],))
        if session["status"] != "PLANNED": raise ValueError("Session is already completed")
        if run["current_state"] not in {"SESSION", "EVALUATION"}: raise ValueError("Session is not active")
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/orchestrator.py
        self.learning.complete(session_id)
        if run["current_state"] == "SESSION":
            self.transition(session["run_id"], "EVALUATION", "peer-learning session completed")
        return self.evaluation.create(session_id)
=======
        generated = self.evaluation.generate_questions(session_id)
        self.learning.complete(session_id)
        if run["current_state"] == "SESSION":
            self.transition(session["run_id"], "EVALUATION", "peer-learning session completed")
        return self.evaluation.create(session_id, generated)
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/orchestrator.py

    def complete_all_sessions(self, run_id: str) -> dict:
        """Complete every planned session in a human-approved batch and create its evaluation."""
        run = self.store.one("SELECT current_state FROM runs WHERE id=?", (run_id,))
        if not run: raise ValueError("Run not found")
        if run["current_state"] not in {"SESSION", "EVALUATION"}:
            raise ValueError("Run has no active sessions")
        session_ids = [row["id"] for row in self.store.all("SELECT id FROM sessions WHERE run_id=? AND status='PLANNED' ORDER BY created_at,id", (run_id,))]
        if not session_ids: raise ValueError("Run has no planned sessions to complete")
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/orchestrator.py
        evaluations = [self.start_evaluation(session_id) for session_id in session_ids]
=======
        # Do all LLM work first: either the whole batch is ready, or no session is completed.
        generated = {session_id: self.evaluation.generate_questions(session_id) for session_id in session_ids}
        evaluations = []
        for session_id in session_ids:
            session = self.store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
            self.learning.complete(session_id)
            current = self.store.one("SELECT current_state FROM runs WHERE id=?", (run_id,))
            if current["current_state"] == "SESSION": self.transition(run_id, "EVALUATION", "peer-learning session completed")
            evaluations.append(self.evaluation.create(session_id, generated[session_id]))
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/orchestrator.py
        return {"run":self.run_view(run_id),"completed_session_count":len(session_ids),"evaluations":evaluations}

    def submit_evaluation(self,evaluation_id:str,post_scores:dict[str,float])->dict:
        evaluation=self.store.one("SELECT * FROM evaluations WHERE id=?",(evaluation_id,));
        if not evaluation or evaluation["status"]!="PENDING": raise ValueError("Evaluation is not pending")
        session=self.store.one("SELECT * FROM sessions WHERE id=?",(evaluation["session_id"],)); candidate=self.candidate(session["candidate_id"])
        run_id=session["run_id"]; relationships=candidate["relationships"]; gains=[]
        for relationship in relationships:
            concept_id=relationship["concept_id"]
            if concept_id not in post_scores: continue
            post=max(0.0,min(1.0,float(post_scores[concept_id]))); pre=relationship["learner_score"]; gain=round(post-pre,4); effective=gain>=self.settings.effective_gain_threshold
            gains.append((relationship,pre,post,gain,effective))
        if not gains: raise ValueError("Post scores must include at least one concept taught in the session")
        effective=all(item[4] for item in gains); now=utcnow()
        with self.store.connection() as conn:
            for rel,pre,post,gain,is_effective in gains:
                conn.execute("INSERT INTO learning_gains(evaluation_id,teacher_id,learner_id,concept_id,pre_score,post_score,gain,effective) VALUES(?,?,?,?,?,?,?,?)",(evaluation_id,rel["teacher_id"],rel["learner_id"],rel["concept_id"],pre,post,gain,int(is_effective)))
                if is_effective: conn.execute("INSERT INTO concept_scores(student_id,concept_id,score,source,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(student_id,concept_id) DO UPDATE SET score=excluded.score,source=excluded.source,updated_at=excluded.updated_at",(rel["learner_id"],rel["concept_id"],post,"evaluation",now))
            result={"effective":effective,"gains":[{"teacher_id":r["teacher_id"],"learner_id":r["learner_id"],"concept_id":r["concept_id"],"pre_score":p,"post_score":po,"gain":g,"effective":e} for r,p,po,g,e in gains]}
            conn.execute("UPDATE evaluations SET status='SUBMITTED',result_json=?,submitted_at=? WHERE id=?",(self.store.dump(result),now,evaluation_id)); conn.execute("INSERT INTO match_history(candidate_id,participants_signature,outcome,created_at,details_json) VALUES(?,?,?,?,?)",(candidate["id"],candidate["participant_signature"],"EFFECTIVE" if effective else "INEFFECTIVE",now,self.store.dump({"average_gain":sum(x[3] for x in gains)/len(gains)})))
        pending_sessions = self.store.all("SELECT s.id FROM sessions s LEFT JOIN evaluations e ON e.session_id=s.id WHERE s.run_id=? AND (e.status IS NULL OR e.status!='SUBMITTED')", (run_id,))
        if pending_sessions:
            return {"result":result,"run":self.run_view(run_id),"rematch":None,"batch_pending_session_ids":[row["id"] for row in pending_sessions]}
        batch_results = self.store.all("SELECT result_json FROM evaluations e JOIN sessions s ON s.id=e.session_id WHERE s.run_id=?", (run_id,))
        batch_effective = all(self.store.load(row["result_json"])["effective"] for row in batch_results)
        result["batch_effective"] = batch_effective
        if batch_effective:
            self.transition(run_id,"UPDATED_PROFILE","effective learning gains")
            self.graph.rebuild(); self.transition(run_id,"FINISHED","profile and graph updated")
            return {"result":result,"run":self.run_view(run_id),"rematch":None}
        self.transition(run_id,"MATCHING","ineffective learning causes rematch")
        return {"result":result,"run":self.run_view(run_id),"rematch":self.run_matching("ineffective session",run_id)}

    def submit_all_evaluations(self, run_id: str, submissions: list[dict]) -> dict:
        """Validate and submit every outstanding evaluation in one approved-session batch."""
        run = self.store.one("SELECT current_state FROM runs WHERE id=?", (run_id,))
        if not run: raise ValueError("Run not found")
        if run["current_state"] != "EVALUATION": raise ValueError("Run is not awaiting evaluations")
        pending_ids = {row["id"] for row in self.store.all("SELECT e.id FROM evaluations e JOIN sessions s ON s.id=e.session_id WHERE s.run_id=? AND e.status='PENDING'", (run_id,))}
        supplied = {submission["evaluation_id"] for submission in submissions}
        if len(supplied) != len(submissions): raise ValueError("Each evaluation may be submitted only once")
        if supplied != pending_ids:
            missing = sorted(pending_ids-supplied); extra = sorted(supplied-pending_ids)
            raise ValueError(f"Submit exactly the pending evaluations; missing={missing}, invalid={extra}")
        results = []
        for submission in submissions:
            results.append(self.submit_evaluation(submission["evaluation_id"], submission["post_scores"]))
        final = results[-1]
        return {"submitted_evaluation_count":len(results),"evaluation_results":[result["result"] for result in results],"run":final["run"],"rematch":final["rematch"]}

    def run_view(self,run_id:str)->dict:
        run=self.store.one("SELECT * FROM runs WHERE id=?",(run_id,));
        if not run: raise ValueError("Run not found")
        run["metadata"]=self.store.load(run.pop("metadata_json")); run["transitions"]=self.store.all("SELECT from_state,to_state,reason,created_at FROM transitions WHERE run_id=? ORDER BY id",(run_id,)); return run
