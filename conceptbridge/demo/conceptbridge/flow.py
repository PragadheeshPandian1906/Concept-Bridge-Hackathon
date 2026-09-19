"""FLOW - the ConceptBridge state machine.

    INPUT -> PROFILING -> MATCHING -> WAITING_FOR_APPROVAL
                             ^              |
                             |      approve |  reject
                             |              v     |
                             |           SESSION  |
                             |              |     |
                             |         EVALUATION |
                             |          |      |  |
                             |  effective|  ineffective
                             |          v      |__|
                             |   UPDATED_PROFILE
                             |          |
                             |          v
                             |       FINISHED
                             |
                  MATCHING -> NO_SUITABLE_MATCH   (terminal)

flow.py owns: state handlers, transitions, the domain revision limit,
domain failure conditions and message building.

flow.py does NOT own: HTTP requests, the database format, or environment
parsing. Those live in ``slice/``.
"""

from __future__ import annotations

from slice.errors import SliceError
from slice.records import RecordKind
from slice.runner import RunContext, StateMachine

from . import evaluation, matching, profiling, session
from .schema import (Approval, Failure, MatchCandidate, RunInput, SessionPlan,
                     State, StudentProfile)

#: DOMAIN bound - how many times the agent may go back to MATCHING after a
#: rejected or ineffective pairing. This is deliberately separate from the
#: infrastructure token/attempt budget in slice/budget.py.
MAX_REMATCH_ATTEMPTS = 2

BAR = "=" * 58


# ----------------------------------------------------------- helpers
def profiles_from_ctx(ctx: RunContext) -> list[StudentProfile]:
    return [StudentProfile.model_validate(p) for p in ctx.data.get("profiles", [])]


def profile_map(ctx: RunContext) -> dict[str, StudentProfile]:
    return {p.student_id: p for p in profiles_from_ctx(ctx)}


def store_profiles(ctx: RunContext, profiles: list[StudentProfile]) -> None:
    ctx.data["profiles"] = [p.model_dump() for p in profiles]


def current_candidate(ctx: RunContext) -> MatchCandidate | None:
    raw = ctx.data.get("candidate")
    return MatchCandidate.model_validate(raw) if raw else None


def fail(ctx: RunContext, reason: str) -> str:
    ctx.record(RecordKind.FAILURE, Failure(reason=reason, state=ctx.state))
    ctx.log(f"\nFAILED: {reason}")
    return State.FAILED


def out_of_rematches(ctx: RunContext) -> bool:
    return ctx.data.get("rematch_count", 0) > MAX_REMATCH_ATTEMPTS


def llm_event_logger(ctx: RunContext):
    def on_event(event: dict):
        ctx.record(RecordKind.LLM_CALL, event)
        if event.get("event") == "model_failed":
            ctx.log(f"    model failed ({event.get('model')}), trying fallback")
        elif event.get("event") == "schema_invalid":
            ctx.log("    structured output invalid, attempting schema repair")
        elif event.get("event") == "llm_degraded":
            ctx.log(f"    model unavailable for {event.get('step')}; "
                    f"using deterministic fallback")
    return on_event


# ---------------------------------------------------------- handlers
def handle_input(ctx: RunContext) -> str:
    ctx.log(f"\n{BAR}\nCONCEPTBRIDGE AGENT\n{BAR}\nRun ID: {ctx.run_id}\n")
    run_input = RunInput(
        run_id=ctx.run_id,
        quiz_path=str(ctx.data.get("quiz_path")),
        concept_map_path=str(ctx.data.get("concept_map_path")),
        scenario=ctx.data.get("scenario", "success"),
        students=ctx.data.get("students") or [],
        mode=ctx.data.get("mode", "stub"),
    )
    try:
        rows = profiling.load_quiz(run_input.quiz_path)
    except profiling.ProfilingError as exc:
        return fail(ctx, f"input error: {exc}")

    ctx.data["quiz_rows"] = len(rows)
    ctx.record(RecordKind.INPUT, run_input)
    ctx.log(f"[1/8] INPUT\n      Loaded {len(rows)} quiz answers from "
            f"{run_input.quiz_path}")
    return State.PROFILING


def handle_profiling(ctx: RunContext) -> str:
    try:
        profiles = profiling.profile_students(
            ctx.data["quiz_path"], ctx.data["concept_map_path"],
            ctx.data.get("students") or None,
        )
    except profiling.ProfilingError as exc:
        return fail(ctx, f"profiling error: {exc}")

    store_profiles(ctx, profiles)
    ctx.data.setdefault("original_profiles", ctx.data["profiles"])
    for profile in profiles:
        ctx.versioned_record(RecordKind.STUDENT_PROFILE, profile)

    ctx.log(f"\n[2/8] PROFILING\n      Generated profiles for "
            f"{len(profiles)} students (deterministic aggregation)")
    for profile in profiles:
        scores = "  ".join(f"{c.concept} {c.score:.2f}" for c in profile.concepts)
        ctx.log(f"      {profile.student_name:<8} {scores}")
    return State.MATCHING


def handle_matching(ctx: RunContext) -> str:
    attempt = ctx.data.get("rematch_count", 0)
    if out_of_rematches(ctx):
        ctx.log(f"\n[3/8] MATCHING\n      Re-matching limit "
                f"({MAX_REMATCH_ATTEMPTS}) reached; stopping.")
        ctx.record(RecordKind.NOTE, {"reason": "rematch limit reached",
                                     "attempts": attempt})
        return State.NO_SUITABLE_MATCH

    profiles = profiles_from_ctx(ctx)
    excluded = ctx.data.get("excluded", [])
    candidates = matching.generate_candidates(profiles, excluded)

    label = "MATCHING" if attempt == 0 else f"MATCHING (re-match {attempt})"
    ctx.log(f"\n[3/8] {label}")
    if excluded:
        ctx.log(f"      Excluded pairs: {', '.join(excluded)}")

    if not candidates.items:
        ctx.log("      No reciprocal pair remains.")
        ctx.record(RecordKind.NOTE, {"reason": "no eligible candidates",
                                     "excluded": list(excluded)})
        return State.NO_SUITABLE_MATCH

    candidate = candidates.items[0]
    people = profile_map(ctx)
    a, b = people[candidate.student_a], people[candidate.student_b]

    ctx.data["candidate"] = candidate.model_dump()
    ctx.versioned_record(RecordKind.MATCH_CANDIDATE, candidate)

    ctx.log(f"      {len(candidates.items)} eligible pair(s); best first.")
    ctx.log(f"\n      Candidate: {a.student_name} <-> {b.student_name}")
    ctx.log(f"      Compatibility: {candidate.compatibility_score:.2f} "
            f"(a->b {candidate.a_to_b_score:.2f}, b->a "
            f"{candidate.b_to_a_score:.2f}, balance {candidate.balance:.2f})")
    ctx.log(f"      {a.student_name} teaches: {', '.join(candidate.a_teaches)}")
    ctx.log(f"      {b.student_name} teaches: {', '.join(candidate.b_teaches)}")

    text, source = session.explain_match(
        candidate, a, b, config=ctx.config, budget=ctx.budget,
        provider=ctx.provider, use_llm=ctx.data.get("use_llm", True),
        on_event=llm_event_logger(ctx),
    )
    ctx.data["explanation"] = text
    ctx.versioned_record(RecordKind.MATCH_EXPLANATION,
                         {"match_id": candidate.match_id, "source": source,
                          "text": text})
    ctx.log(f"\n      Reason ({source}):")
    for line in text.splitlines():
        ctx.log(f"        {line}")
    return State.WAITING_FOR_APPROVAL


def _read_approval(ctx: RunContext) -> tuple[bool | None, str]:
    """Return ``(approved, answered_by)``. ``None`` means no answer available."""
    script = ctx.data.get("approval_script") or []
    if script:
        answer = script.pop(0) if len(script) > 1 else script[0]
        ctx.data["approval_script"] = script
        return answer.strip().lower() in ("y", "yes", "true", "1"), "cli-flag"

    if not ctx.data.get("interactive", True):
        return None, "none"

    try:
        answer = input("      Approve this match? [y/n]: ")
    except (EOFError, KeyboardInterrupt):
        return None, "none"
    return answer.strip().lower() in ("y", "yes"), "human-cli"


def handle_waiting_for_approval(ctx: RunContext) -> str:
    candidate = current_candidate(ctx)
    if candidate is None:
        return fail(ctx, "no candidate to approve")

    ctx.log("\n[4/8] WAITING_FOR_APPROVAL")
    approved, answered_by = _read_approval(ctx)
    if approved is None:
        return fail(ctx, "no approval answer available (never auto-approve)")

    approval = Approval(match_id=candidate.match_id, approved=approved,
                        answered_by=answered_by)
    ctx.versioned_record(RecordKind.APPROVAL, approval)

    if approved:
        ctx.log(f"      APPROVED by {answered_by}")
        return State.SESSION

    ctx.log(f"      REJECTED by {answered_by} -> returning to MATCHING")
    ctx.data.setdefault("excluded", []).append(candidate.match_id)
    ctx.data["rematch_count"] = ctx.data.get("rematch_count", 0) + 1
    ctx.data["candidate"] = None
    return State.MATCHING


def handle_session(ctx: RunContext) -> str:
    candidate = current_candidate(ctx)
    if candidate is None:
        return fail(ctx, "no approved candidate for session generation")

    people = profile_map(ctx)
    a, b = people[candidate.student_a], people[candidate.student_b]
    ctx.log("\n[5/8] SESSION\n      Generating peer-learning session...")

    try:
        plan, source = session.generate_session(
            candidate, a, b, config=ctx.config, budget=ctx.budget,
            provider=ctx.provider, use_llm=ctx.data.get("use_llm", True),
            on_event=llm_event_logger(ctx),
        )
    except SliceError as exc:
        return fail(ctx, f"session generation failed: {exc}")

    ctx.data["session"] = plan.model_dump()
    ctx.versioned_record(RecordKind.SESSION,
                         {"source": source, **plan.model_dump()})

    ctx.log(f"      Source: {source}")
    for direction in plan.teaching_directions:
        ctx.log(f"      {direction}")
    ctx.log("      Objectives:")
    for objective in plan.learning_objectives:
        ctx.log(f"        - {objective}")
    ctx.log(f"      Shared challenge: {plan.shared_challenge}")
    return State.EVALUATION


def handle_evaluation(ctx: RunContext) -> str:
    candidate = current_candidate(ctx)
    if candidate is None:
        return fail(ctx, "no candidate to evaluate")

    people = profile_map(ctx)
    a, b = people[candidate.student_a], people[candidate.student_b]
    outcome = evaluation.evaluate_match(
        candidate, a, b, scenario=ctx.data.get("scenario", "success"),
    )
    ctx.data["outcome"] = outcome.model_dump()
    ctx.versioned_record(RecordKind.OUTCOME, outcome)

    ctx.log("\n[6/8] EVALUATION")
    for item in outcome.outcomes:
        name = people[item.student_id].student_name
        ctx.log(f"      {name}: {item.concept} {item.before_score:.2f} -> "
                f"{item.after_score:.2f}  gain {item.gain:+.2f}")
    ctx.log(f"      Threshold: {evaluation.LEARNING_GAIN_THRESHOLD:+.2f}")

    if outcome.effective:
        ctx.log("      MATCH EFFECTIVE")
        return State.UPDATED_PROFILE

    ctx.log("      MATCH INEFFECTIVE -> returning to MATCHING")
    ctx.data.setdefault("excluded", []).append(candidate.match_id)
    ctx.data["rematch_count"] = ctx.data.get("rematch_count", 0) + 1
    ctx.data["candidate"] = None
    ctx.data["session"] = None
    return State.MATCHING


def handle_updated_profile(ctx: RunContext) -> str:
    outcome_raw = ctx.data.get("outcome")
    if not outcome_raw:
        return fail(ctx, "no outcome to apply")

    from .schema import SessionOutcome
    outcome = SessionOutcome.model_validate(outcome_raw)
    people = profile_map(ctx)
    updates = evaluation.build_profile_updates(outcome, people)
    updated = evaluation.apply_updates(people, updates)
    store_profiles(ctx, [updated[k] for k in sorted(updated)])

    ctx.log("\n[7/8] UPDATED_PROFILE")
    for update in updates:
        ctx.versioned_record(RecordKind.PROFILE_UPDATE, update)
        ctx.log(f"      {people[update.student_id].student_name}: "
                f"{update.concept} {update.old_score:.2f} -> "
                f"{update.new_score:.2f}")
    return State.FINISHED


def handle_terminal_banner(ctx: RunContext) -> None:
    if ctx.state == State.FINISHED:
        ctx.log(f"\n[8/8] FINISHED\n{BAR}")
    elif ctx.state == State.NO_SUITABLE_MATCH:
        ctx.log(f"\n[8/8] NO_SUITABLE_MATCH (terminal)\n{BAR}")
    elif ctx.state == State.FAILED:
        ctx.log(f"\n[8/8] FAILED (terminal)\n{BAR}")


# ------------------------------------------------------- the machine
def build_machine(max_steps: int = 40) -> StateMachine:
    machine = StateMachine(initial=State.INPUT, terminal=State.TERMINAL,
                           max_steps=max_steps)
    machine.register(State.INPUT, handle_input)
    machine.register(State.PROFILING, handle_profiling)
    machine.register(State.MATCHING, handle_matching)
    machine.register(State.WAITING_FOR_APPROVAL, handle_waiting_for_approval)
    machine.register(State.SESSION, handle_session)
    machine.register(State.EVALUATION, handle_evaluation)
    machine.register(State.UPDATED_PROFILE, handle_updated_profile)
    return machine
