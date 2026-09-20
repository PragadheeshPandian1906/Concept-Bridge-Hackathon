from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .agents.profiling import ConceptProfilingAgent
from .config import get_settings
from .db import Store, utcnow
from .graph import KnowledgeGraph
from .orchestrator import Orchestrator
from .schemas import AnswerSubmit, ApproveRequest, ConceptCreate, EvaluationBatchSubmit, EvaluationSubmit, QuestionCreate, RejectRequest, ScoreUpsert, StudentCreate

settings=get_settings(); store=Store(settings); profiling=ConceptProfilingAgent(store,settings); graph=KnowledgeGraph(store,settings); orchestrator=Orchestrator(store,settings)

def _error(exc: Exception):
    raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 409,detail=str(exc))

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize(); yield

app=FastAPI(title="ConceptBridge",version="1.0.0",lifespan=lifespan)

@app.get("/health")
def health(): return {"status":"ok"}

@app.post("/api/v1/students",status_code=201)
def create_student(payload:StudentCreate):
    try:
        with store.connection() as conn: conn.execute("INSERT INTO students(id,name,email,metadata_json,created_at) VALUES(?,?,?,?,?)",(payload.id,payload.name,payload.email,store.dump(payload.metadata),utcnow()))
    except Exception as exc: _error(exc)
    return payload

@app.get("/api/v1/students")
def list_students():
    rows=store.all("SELECT id,name,email,metadata_json,created_at FROM students ORDER BY id")
    return [{**r,"metadata":store.load(r.pop("metadata_json"))} for r in rows]

@app.put("/api/v1/students/{student_id}/scores")
def set_score(student_id:str,payload:ScoreUpsert):
    if not store.one("SELECT id FROM students WHERE id=?",(student_id,)): raise HTTPException(404,"Student not found")
    if not store.one("SELECT id FROM concepts WHERE id=?",(payload.concept_id,)): raise HTTPException(404,"Concept not found")
    with store.connection() as conn: conn.execute("INSERT INTO concept_scores(student_id,concept_id,score,source,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(student_id,concept_id) DO UPDATE SET score=excluded.score,source=excluded.source,updated_at=excluded.updated_at",(student_id,payload.concept_id,payload.score,payload.source,utcnow()))
    return {"student_id":student_id,**payload.model_dump()}

@app.post("/api/v1/concepts",status_code=201)
def create_concept(payload:ConceptCreate):
    try:
        with store.connection() as conn: conn.execute("INSERT INTO concepts(id,name,description) VALUES(?,?,?)",(payload.id,payload.name,payload.description))
    except Exception as exc: _error(exc)
    return payload

@app.get("/api/v1/concepts")
def list_concepts(): return store.all("SELECT * FROM concepts ORDER BY name")

@app.post("/api/v1/questions",status_code=201)
def create_question(payload:QuestionCreate):
    try:
        with store.connection() as conn: conn.execute("INSERT INTO questions(id,concept_id,type,text,correct_answer,max_marks,rubric,created_at) VALUES(?,?,?,?,?,?,?,?)",(payload.id,payload.concept_id,payload.type,payload.text,payload.correct_answer,payload.max_marks,payload.rubric,utcnow()))
    except Exception as exc: _error(exc)
    return payload

@app.post("/api/v1/questions/{question_id}/answers")
def submit_answer(question_id:str,payload:AnswerSubmit):
    try: return profiling.score_answer(payload.student_id,question_id,payload.answer)
    except ValueError as exc: _error(exc)

@app.post("/api/v1/profiling/run")
def run_profiling(): return {"profiles_updated":profiling.build_profiles()}

@app.post("/api/v1/graph/rebuild")
def rebuild_graph(): return {"active_edges":graph.rebuild(),"metrics":graph.metrics()}

@app.get("/api/v1/graph")
def get_graph(): return {"edges":graph.active_edges(),"metrics":graph.metrics()}

@app.post("/api/v1/matching/run")
def run_matching(): return orchestrator.run_matching()

@app.get("/api/v1/matching/{candidate_id}")
def get_candidate(candidate_id:str):
    try:return orchestrator.candidate(candidate_id)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/matching/{candidate_id}/approve")
def approve(candidate_id:str,payload:ApproveRequest):
    try:return orchestrator.approve(candidate_id,payload.actor,payload.duration_minutes)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/matching/runs/{run_id}/approve-all")
def approve_all(run_id:str,payload:ApproveRequest):
    try:return orchestrator.approve_all(run_id,payload.actor,payload.duration_minutes)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/matching/{candidate_id}/reject")
def reject(candidate_id:str,payload:RejectRequest):
    try:return orchestrator.reject(candidate_id,payload.actor,payload.reason)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/sessions/{session_id}/complete")
def complete_session(session_id:str):
    try:return orchestrator.start_evaluation(session_id)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/matching/runs/{run_id}/sessions/complete-all")
def complete_all_sessions(run_id:str):
    try:return orchestrator.complete_all_sessions(run_id)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/evaluations/{evaluation_id}/submit")
def submit_evaluation(evaluation_id:str,payload:EvaluationSubmit):
    try:return orchestrator.submit_evaluation(evaluation_id,payload.post_scores)
    except ValueError as exc:_error(exc)

@app.post("/api/v1/matching/runs/{run_id}/evaluations/submit-all")
def submit_all_evaluations(run_id:str,payload:EvaluationBatchSubmit):
    try:return orchestrator.submit_all_evaluations(run_id,[item.model_dump() for item in payload.evaluations])
    except ValueError as exc:_error(exc)

@app.get("/api/v1/runs/{run_id}")
def get_run(run_id:str):
    try:return orchestrator.run_view(run_id)
    except ValueError as exc:_error(exc)

@app.get("/api/v1/analytics")
def analytics():
    return {"graph":graph.metrics(),"runs":store.all("SELECT id,root_id,iteration,current_state,trigger,created_at FROM runs ORDER BY created_at DESC"),"history":store.all("SELECT * FROM match_history ORDER BY id DESC")}
