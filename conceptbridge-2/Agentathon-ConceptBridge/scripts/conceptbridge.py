from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.conceptbridge.flow import ConceptBridgeFlow, JsonState
from demo.conceptbridge.matching import find_candidates
from demo.conceptbridge.profiling import build_profiles
from demo.conceptbridge.schema import State
from demo.conceptbridge.stub import StubModel
from slice.config import settings
from slice.llm import complete

DATA = ROOT / "demo" / "conceptbridge" / "data"
FOLLOWUP = DATA / "followup_quiz.csv"
RUNTIME = ROOT / "runtime" / "conceptbridge"


def main() -> int:
    parser = argparse.ArgumentParser(description="ConceptBridge agentic pilot")
    parser.add_argument("command", choices=["run", "resume", "reset", "inspect"])
    parser.add_argument("--stub", action="store_true")
    parser.add_argument("--approval", choices=["yes", "no"])
    parser.add_argument("--scenario", choices=["success", "ineffective", "no-match"], default="success")
    parser.add_argument("--quiz", type=Path, default=DATA / "quiz.csv")
    parser.add_argument("--question-concepts", type=Path, default=DATA / "question_concepts.csv")
    parser.add_argument("--followup-quiz", type=Path, default=FOLLOWUP)
    args = parser.parse_args()
    store = JsonState(RUNTIME / "state.json", RUNTIME / "records.jsonl")
    if args.command == "reset":
        shutil.rmtree(RUNTIME, ignore_errors=True)
        print("ConceptBridge runtime reset.")
        return 0
    if args.command == "inspect":
        print(json.dumps(store.load() or {"state": "EMPTY"}, indent=2))
        return 0
    provider = StubModel() if args.stub else complete
    flow = ConceptBridgeFlow(store, call=provider, settings=settings(), stub=args.stub)
    if args.command == "run":
        result = flow.start(args.quiz, args.question_concepts, followup_quiz=args.followup_quiz)
        if args.scenario == "no-match":
            profiles = build_profiles(args.quiz, args.question_concepts)
            result["excluded_matches"] = [item.match_id for item in find_candidates(profiles).items]
            result["state"] = State.MATCHING.value
            flow.store.save(result)
        approval = None if args.approval is None else args.approval == "yes"
        result = _interactive_advance(flow, result, approval, args.scenario, args.stub,
                                      interactive=args.approval is None)
    else:
        result = _interactive_advance(flow, flow.data, None, args.scenario, args.stub,
                                      interactive=True)
    if result.get("outcomes"):
        outcome = result["outcomes"][-1]
        print("\n=== EVALUATION ===")
        for item in outcome["outcomes"]:
            print(f"{item['student_id']} / {item['concept']}: "
                  f"{item['before_score']:.2f} -> {item['after_score']:.2f} "
                  f"(gain {item['gain']:+.2f})")
        print("Result: " + ("EFFECTIVE" if outcome["effective"] else "INEFFECTIVE"))
    if result.get("profile_updates"):
        print("\n=== UPDATED PROFILE ===")
        for item in result["profile_updates"]:
            print(f"{item['student_id']} / {item['concept']}: {item['new_score']:.2f}")
    print(f"Run ID: {result['run_id']}\nState: {result['state']}")
    print("Transitions and records: runtime/conceptbridge/records.jsonl")
    return 0


def _interactive_advance(flow, result, approval, scenario, stub, interactive=True):
    """Drive a run one human decision at a time while preserving CLI flags."""
    if State(result["state"]) is State.MATCHING:
        result = flow.advance()
    if State(result["state"]) is State.WAITING_FOR_APPROVAL:
        candidate = result["candidate"]
        print("\n=== WAITING FOR APPROVAL ===")
        print(f"Recommended match: {candidate['student_a']} <-> {candidate['student_b']}")
        print(f"Compatibility: {candidate['compatibility_score']:.2f}")
        print(f"{candidate['student_a']} teaches: {', '.join(candidate['a_teaches'])}")
        print(f"{candidate['student_b']} teaches: {', '.join(candidate['b_teaches'])}")
        print(f"Reason: {candidate['rationale']}")
        if approval is None:
            approval = input("Approve this match? [y/n]: ").strip().lower() in {"y", "yes"}
        result = flow.advance(approval, scenario, pause_after_session=interactive)
    if interactive and State(result["state"]) is State.EVALUATION and result.get("sessions"):
        plan = result["sessions"][-1]
        print("\n=== SESSION ===")
        print("Learning objectives:")
        for objective in plan["learning_objectives"]:
            print(f"- {objective}")
        print("Teaching directions:")
        for direction in plan["teaching_directions"]:
            print(f"- {direction}")
        print("Teaching prompts:")
        for prompt in plan["teaching_prompts"]:
            print(f"- {prompt}")
        print(f"Shared challenge: {plan['shared_challenge']}")
        print("Follow-up questions:")
        for question in plan["follow_up_questions"]:
            print(f"- {question}")
        if stub and scenario != "success":
            print("\nUsing the scripted ineffective follow-up scores.")
            return flow.advance(scenario=scenario)
        observations = _collect_observations(flow, result)
        result = flow.advance(scenario=scenario, observations=observations)
    return result


def _collect_observations(flow, result):
    candidate = result["candidate"]
    observations = []
    profiles = result["profiles"]
    for student_id, concepts in ((candidate["student_a"], candidate["b_teaches"]),
                                 (candidate["student_b"], candidate["a_teaches"])):
        scores = {item["concept"]: item["score"] for item in profiles[student_id]["concepts"]}
        for concept in concepts:
            before = scores[concept]
            while True:
                raw = input(f"{student_id} {concept} post-session score (0-1, before {before:.2f}): ").strip()
                try:
                    after = float(raw)
                    if 0 <= after <= 1:
                        break
                except ValueError:
                    pass
                print("Enter a number from 0 to 1, for example 0.75.")
            observations.append((student_id, concept, before, after))
    return observations


if __name__ == "__main__":
    raise SystemExit(main())