"""End-to-end lifecycle demo. Works with no API key (DEMO_MODE=true)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.conceptbridge import orchestrator  # noqa: E402
from demo.conceptbridge.evaluation import agent as evaluation_agent  # noqa: E402
from demo.conceptbridge.matchmaking import graph as G  # noqa: E402
from demo.conceptbridge.peer_learning import agent as peer_agent  # noqa: E402
from demo.conceptbridge.persistence.database import SessionLocal, reset_db  # noqa: E402
from demo.conceptbridge.seed import demo_data  # noqa: E402
from demo.conceptbridge.state import RunState, create_run, load_state  # noqa: E402


def rule(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def main() -> None:
    reset_db()
    db = SessionLocal()

    rule("1. SEED")
    print(demo_data.seed(db))

    run = create_run(db)
    run_id = run.run_id
    print(f"run_id = {run_id}   state = {load_state(db, run_id).value}")

    rule("2. QUIZ SUBMISSION  (INPUT)")
    answers = demo_data.quiz_answers(run_id)
    print("stored answers:", demo_data.store_answers(db, run_id, answers))

    rule("3. PROFILING  (INPUT -> PROFILING -> MATCHING)")
    result = orchestrator.run_profiling(db, run_id)
    print(f"students profiled: {result['students_profiled']}  open-ended LLM calls: {result['llm_calls']}")
    for sid, vector in sorted(result["profiles"].items()):
        print(" ", sid, {k: round(v, 2) for k, v in sorted(vector.items())})

    rule("4. GRAPH + MATCHMAKING  (deterministic, no LLM)")
    matching = orchestrator.run_matching(db, run_id)
    print("graph health:", json.dumps(matching["health"], indent=2))
    print("reciprocal pairs:", [p["students"] for p in G.reciprocal_pairs(db)])
    print("cycles (first 5):", G.find_cycles(db)[:5])
    print("hubs:", [(h["student_id"], h["out_degree"]) for h in G.knowledge_hubs(db)])
    print("bottlenecks:", [(b["concept"], b["ratio"]) for b in G.concept_bottlenecks(db)])
    print("isolated:", G.isolated_students(db))

    match = matching["match"]
    if match is None:
        print("NO MATCH FOUND")
        return
    rule("5. PROPOSED MATCH  (WAITING_FOR_APPROVAL)")
    print("group:", match["members"], " score:", match["score"])
    for rel in match["relationships"]:
        print(f"  {rel['teacher']} -> {rel['learner']}  {rel['concept']}  gap {rel['gap']}")
    print("why this group:", json.dumps(match["components"], indent=2))

    rule("6. HUMAN APPROVAL -> SESSION")
    orchestrator.approve_match(db, match["id"], "demo-instructor", "auto-approved in demo mode")
    session = orchestrator.generate_session(db, match["id"])
    print("session:", session.id, "| objective:", session.plan["objective"])
    for r in session.plan["rounds"]:
        print(f"  round: {r['teacher']} teaches {r['learner']} - {r['concept']}")
    peer_agent.start_session(db, session.id)
    orchestrator.complete_session(db, session.id)
    print("state:", load_state(db, run_id).value)

    rule("7. EVALUATION  (effective path)")
    evaluation = evaluation_agent.generate_evaluation(db, session.id)
    public = evaluation_agent.public_questions(evaluation)
    print(f"generated {len(public)} follow-up questions")
    result = orchestrator.submit_evaluation(
        db, evaluation.id, demo_data.simulated_evaluation_answers(evaluation.questions, learned=True)
    )
    for g in result["per_concept"]:
        print(f"  {g['learner']} / {g['concept_id']}: {g['pre_score']} -> {g['post_score']}  gain {g['gain']}")
    print("average gain:", result["average_gain"], "| effective:", result["effective"])
    print("profile updates:", result["profile_updates"])
    print("state:", load_state(db, run_id).value)

    rule("8. DYNAMIC GRAPH UPDATE")
    print("graph health after learning:", json.dumps(G.graph_health(db), indent=2))

    rule("9. INEFFECTIVE SESSION -> AUTOMATIC REMATCH")
    run2 = create_run(db).run_id
    orchestrator.run_profiling(db, run2)  # no new answers: profiles stay as they are
    orchestrator.run_matching(db, run2)
    from demo.conceptbridge.persistence.models import MatchCandidate

    m2 = (
        db.query(MatchCandidate)
        .filter(MatchCandidate.run_id == run2, MatchCandidate.status == "PROPOSED")
        .first()
    )
    orchestrator.approve_match(db, m2.id, "demo-instructor")
    s2 = orchestrator.generate_session(db, m2.id)
    orchestrator.complete_session(db, s2.id)
    e2 = evaluation_agent.generate_evaluation(db, s2.id)
    r2 = orchestrator.submit_evaluation(
        db, e2.id, demo_data.simulated_evaluation_answers(e2.questions, learned=False)
    )
    print("average gain:", r2["average_gain"], "| effective:", r2["effective"])
    print("state after ineffective evaluation:", load_state(db, run2).value, "(back to MATCHING)")

    rule("10. NO MATCH FOUND")
    run3 = create_run(db).run_id
    orchestrator.run_profiling(db, run3)
    out = orchestrator.run_matching(db, run3, student_ids=["S008"])
    print("state:", out["state"])
    if out["state"] == RunState.NO_MATCH_FOUND.value:
        orchestrator.finish_no_match(db, run3)
    print("final state:", load_state(db, run3).value)

    rule("DONE")
    print("artifacts written to runtime/artifacts/<run_id>/")
    db.close()


if __name__ == "__main__":
    main()
