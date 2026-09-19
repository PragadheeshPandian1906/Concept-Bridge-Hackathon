"""Entry points: run, resume, inspect, reset.

``scripts/conceptbridge.py`` is a thin argparse wrapper over this module,
so tests can drive the agent without a subprocess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slice.budget import Budget
from slice.config import Config, load_config
from slice.records import new_run_id
from slice.runner import RunContext
from slice.store import Store

from . import flow, profiling
from .schema import State
from .stub import make_provider

DEFAULT_RUNTIME = Path("runtime/conceptbridge")

#: scenario -> (approval answers, followup scenario key, student filter)
SCENARIOS = {
    "success": (["yes"], "success", None),
    "reject": (["no", "yes"], "success", None),
    "ineffective": (["yes"], "ineffective", None),
    "no-match": (["yes"], "success", ["Arjun", "Priya"]),
}


@dataclass
class RunOptions:
    stub: bool = True
    stub_mode: str = "ok"
    scenario: str = "success"
    approval: str | None = None          # "yes" | "no" | "no,yes"
    interactive: bool = False
    use_llm: bool = True
    runtime: str | Path = DEFAULT_RUNTIME
    quiz_path: str | Path = profiling.QUIZ_CSV
    concept_map_path: str | Path = profiling.CONCEPT_MAP_CSV
    students: list[str] | None = None
    stop_after: str | None = None
    max_steps: int = 40
    log: object = print
    config: Config | None = None
    provider: object = None


def _quiet(_msg: str) -> None:
    pass


def build_context(options: RunOptions) -> RunContext:
    if options.scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {options.scenario!r}; "
                         f"choose from {sorted(SCENARIOS)}")
    answers, followup_scenario, scenario_students = SCENARIOS[options.scenario]
    if options.approval:
        answers = [a.strip() for a in options.approval.split(",") if a.strip()]

    config = options.config or load_config()
    store = Store(options.runtime)
    provider = options.provider or make_provider(options.stub, options.stub_mode)

    ctx = RunContext(
        run_id=new_run_id(),
        state=State.INPUT,
        store=store,
        config=config,
        budget=Budget.from_config(config),
        provider=provider,
        log=options.log or _quiet,
        stop_after=options.stop_after,
        data={
            "quiz_path": str(options.quiz_path),
            "concept_map_path": str(options.concept_map_path),
            "scenario": followup_scenario,
            "scenario_name": options.scenario,
            "students": options.students or scenario_students or [],
            "approval_script": list(answers),
            "interactive": bool(options.interactive),
            "use_llm": bool(options.use_llm),
            "mode": "stub" if options.stub else "live",
            "excluded": [],
            "rematch_count": 0,
        },
    )
    return ctx


def run(options: RunOptions | None = None, **kwargs) -> RunContext:
    """Start a fresh run (clears the previous workspace)."""
    options = options or RunOptions(**kwargs)
    ctx = build_context(options)
    if not options.stub and options.use_llm and not ctx.config.has_api_key:
        ctx.log("WARNING: OPENROUTER_API_KEY is not set. Live model calls will "
                "fail and the agent will use its deterministic fallbacks.\n"
                "         Use --stub for a clean offline run.")
    ctx.store.reset()
    machine = flow.build_machine(max_steps=options.max_steps)
    ctx = machine.run(ctx)
    flow.handle_terminal_banner(ctx)
    return ctx


def resume(options: RunOptions | None = None, **kwargs) -> RunContext:
    """Continue the persisted run from its saved state."""
    options = options or RunOptions(**kwargs)
    store = Store(options.runtime)
    snapshot = store.load_state()
    if snapshot is None:
        raise FileNotFoundError(
            f"no saved state in {store.state_path}; run the agent first"
        )

    config = options.config or load_config()
    budget = Budget.from_config(config)
    saved_budget = snapshot.get("budget") or {}
    budget.used_tokens = int(saved_budget.get("used_tokens", 0))
    budget.used_attempts = int(saved_budget.get("used_attempts", 0))

    ctx = RunContext(
        run_id=snapshot["run_id"],
        state=snapshot["state"],
        store=store,
        config=config,
        budget=budget,
        provider=options.provider or make_provider(options.stub, options.stub_mode),
        log=options.log or _quiet,
        stop_after=options.stop_after,
        data=snapshot.get("data", {}),
        steps=int(snapshot.get("steps", 0)),
    )
    if options.approval:
        ctx.data["approval_script"] = [a.strip() for a in options.approval.split(",")]
    ctx.data["interactive"] = bool(options.interactive)

    ctx.log(f"\nResuming run {ctx.run_id} from state {ctx.state}")
    if ctx.state in State.TERMINAL:
        ctx.log("Run is already in a terminal state; nothing to do.")
        return ctx

    machine = flow.build_machine(max_steps=options.max_steps)
    ctx = machine.run(ctx)
    flow.handle_terminal_banner(ctx)
    return ctx


def inspect(runtime: str | Path = DEFAULT_RUNTIME, log=print) -> dict:
    """Print the persisted state and replay the append-only history."""
    store = Store(runtime)
    snapshot = store.load_state()
    records = store.read_records()

    log("=" * 58)
    log("CONCEPTBRIDGE - PERSISTED STATE")
    log("=" * 58)
    if snapshot is None:
        log(f"No state file at {store.state_path}")
    else:
        log(f"Run ID : {snapshot.get('run_id')}")
        log(f"State  : {snapshot.get('state')}")
        log(f"Steps  : {snapshot.get('steps')}")
        log(f"Budget : {snapshot.get('budget')}")
        data = snapshot.get("data", {})
        log(f"Excluded pairs : {data.get('excluded')}")
        log(f"Re-match count : {data.get('rematch_count')}")
        for profile in data.get("profiles", []):
            scores = "  ".join(f"{c['concept']} {c['score']:.2f}"
                               for c in profile["concepts"])
            log(f"  {profile['student_name']:<8} {scores}")

    log("\nHISTORY (append-only)")
    log("-" * 58)
    for record in records:
        detail = ""
        payload = record.payload
        if record.kind == "state_transition":
            detail = f"{payload.get('from')} -> {payload.get('to')}"
        elif record.kind == "match_candidate":
            detail = (f"{payload.get('match_id')} "
                      f"score={payload.get('compatibility_score')}")
        elif record.kind == "approval":
            detail = (f"{payload.get('match_id')} "
                      f"approved={payload.get('approved')}")
        elif record.kind == "outcome":
            detail = (f"{payload.get('match_id')} "
                      f"effective={payload.get('effective')}")
        elif record.kind == "profile_update":
            detail = (f"{payload.get('student_id')} {payload.get('concept')} "
                      f"{payload.get('old_score')} -> {payload.get('new_score')}")
        elif record.kind == "student_profile":
            detail = payload.get("student_id", "")
        log(f"  {record.state:<21} {record.kind:<18} {detail}")
    log("-" * 58)
    log(f"{len(records)} records in {store.records_path}")
    return {"state": snapshot, "records": len(records)}


def reset(runtime: str | Path = DEFAULT_RUNTIME, log=print) -> None:
    store = Store(runtime)
    store.reset()
    log(f"Cleared {store.state_path} and {store.records_path}")
