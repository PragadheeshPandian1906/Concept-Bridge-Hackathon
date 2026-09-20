from pathlib import Path
import pytest

from demo.conceptbridge.config import Settings
from demo.conceptbridge.db import Store
from demo.conceptbridge.llm import LLMUnavailable
from demo.conceptbridge.orchestrator import Orchestrator


def make_system(tmp_path: Path):
    settings=Settings(database_path=str(tmp_path/"test.db"),min_group_size=2,max_group_size=5,max_teaching_load=10,strict_llm=False,demo_mode=True)
    store=Store(settings); store.initialize()
    with store.connection() as conn:
        conn.execute("INSERT INTO concepts(id,name,description) VALUES('r','Recursion','')")
        for id_,score in [("A",.95),("B",.2),("C",.25),("D",.3),("E",.35),("F",.5),("G",.55),("H",.4)]:
            conn.execute("INSERT INTO students(id,name,email,metadata_json,created_at) VALUES(?,?,?, '{}','now')",(id_,id_,f"{id_}@x"))
            conn.execute("INSERT INTO concept_scores(student_id,concept_id,score,source,updated_at) VALUES(?,?,?,'test','now')",(id_,"r",score))
    return Orchestrator(store,settings)


def test_all_sizes_are_enumerated_and_non_cycle_group_is_valid(tmp_path):
    system=make_system(tmp_path); result=system.run_matching()
    assert result["generation"]["combinations_considered"] == {"2":28,"3":56,"4":70,"5":56}
    # A teaches B/C/D: this has no cycle or reciprocal edge and remains valid.
    group=next(c for c in result["candidates"] if c["participant_ids"] == ["A","B","C","D"])
    assert group["evidence"]["knowledge_cycle"] is False
    assert {r["learner_id"] for r in group["relationships"]} >= {"B","C","D"}


def test_human_rejection_causes_rematch(tmp_path):
    system=make_system(tmp_path); first=system.run_matching(); rejected=first["candidates"][0]
    rematch=system.reject(rejected["id"],"reviewer","broader coverage")
    assert rematch["iteration"] == 2
    assert rematch["current_state"] == "WAITING_FOR_HUMAN_REVIEW"
    assert rejected["signature"] not in [c["signature"] for c in rematch["candidates"]]


def test_human_can_choose_non_top_candidate(tmp_path):
    system=make_system(tmp_path); result=system.run_matching(); chosen=result["candidates"][1]
    approved=system.approve(chosen["id"],"reviewer",45)
    assert approved["candidate"]["status"] == "APPROVED"
    assert approved["run"]["current_state"] == "SESSION"


def test_human_can_approve_all_candidates_in_a_run(tmp_path):
    system=make_system(tmp_path); result=system.run_matching()
    approved=system.approve_all(result["id"],"reviewer",30)
    assert approved["approved_count"] == result["candidate_count"]
    assert len(approved["sessions"]) == result["candidate_count"]
    assert approved["run"]["current_state"] == "SESSION"
    completed=system.complete_all_sessions(result["id"])
    assert completed["completed_session_count"] == result["candidate_count"]
    assert len(completed["evaluations"]) == result["candidate_count"]
    assert completed["run"]["current_state"] == "EVALUATION"


def test_strict_llm_failure_does_not_approve_candidate(tmp_path):
    fallback_system=make_system(tmp_path)
    strict_settings=Settings(database_path=str(tmp_path/"test.db"),min_group_size=2,max_group_size=5,max_teaching_load=10,strict_llm=True, demo_mode=True)
    system=Orchestrator(fallback_system.store, strict_settings)
    result=system.run_matching(); candidate_id=result["candidates"][0]["id"]
    with pytest.raises(LLMUnavailable): system.approve(candidate_id,"reviewer",45)
    assert system.candidate(candidate_id)["status"] == "PENDING"
    assert system.run_view(result["id"])["current_state"] == "WAITING_FOR_HUMAN_REVIEW"
