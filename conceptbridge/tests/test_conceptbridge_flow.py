"""State-machine tests (covers spec TEST 4, 5, 8, 9, 14)."""

from helpers import cleanup, quiet, run_stub, temp_runtime, transitions

from demo.conceptbridge.main import RunOptions, run
from demo.conceptbridge.schema import State
from demo.conceptbridge.stub import StubProvider


def test_approval_yes_reaches_finished():
    """TEST 4 - MATCHING -> WAITING_FOR_APPROVAL -> SESSION."""
    ctx = run_stub(scenario="success", approval="yes")
    assert ctx.state == State.FINISHED
    path = transitions(ctx.store)
    assert (State.MATCHING, State.WAITING_FOR_APPROVAL) in path
    assert (State.WAITING_FOR_APPROVAL, State.SESSION) in path
    assert (State.SESSION, State.EVALUATION) in path
    assert (State.EVALUATION, State.UPDATED_PROFILE) in path
    assert (State.UPDATED_PROFILE, State.FINISHED) in path
    cleanup()


def test_approval_no_moves_backwards_and_excludes_the_pair():
    """TEST 5 - rejection is a backward transition, and the pair is excluded."""
    ctx = run_stub(scenario="reject")
    assert ctx.state == State.FINISHED
    assert (State.WAITING_FOR_APPROVAL, State.MATCHING) in transitions(ctx.store)

    approvals = [r.payload for r in ctx.store.records_of_kind("approval")]
    assert approvals[0]["approved"] is False
    assert "S1|S2" in ctx.data["excluded"]

    chosen = [r.payload["match_id"] for r in ctx.store.records_of_kind("match_candidate")]
    assert chosen[0] == "S1|S2"
    assert chosen[1] != "S1|S2"          # never offered twice
    cleanup()


def test_rematching_after_an_ineffective_session():
    """TEST 8 - ineffective outcome sends the agent back to MATCHING."""
    ctx = run_stub(scenario="ineffective")
    assert ctx.state == State.FINISHED
    assert (State.EVALUATION, State.MATCHING) in transitions(ctx.store)

    outcomes = [r.payload for r in ctx.store.records_of_kind("outcome")]
    assert outcomes[0]["effective"] is False
    assert outcomes[1]["effective"] is True
    assert outcomes[0]["match_id"] != outcomes[1]["match_id"]
    assert ctx.data["rematch_count"] == 1
    cleanup()


def test_no_suitable_match_is_terminal():
    """TEST 9 - a roster with no reciprocal pair ends cleanly."""
    ctx = run_stub(scenario="no-match")
    assert ctx.state == State.NO_SUITABLE_MATCH
    assert ctx.store.records_of_kind("match_candidate") == []
    cleanup()


def test_repeated_rejection_stops_at_the_domain_limit():
    """The agent never loops forever: MAX_REMATCH_ATTEMPTS bounds it."""
    from demo.conceptbridge.flow import MAX_REMATCH_ATTEMPTS
    ctx = run_stub(scenario="success", approval="no")
    assert ctx.state == State.NO_SUITABLE_MATCH
    assert ctx.data["rematch_count"] == MAX_REMATCH_ATTEMPTS + 1
    assert len(ctx.store.records_of_kind("approval")) == MAX_REMATCH_ATTEMPTS + 1
    cleanup()


def test_domain_limit_is_not_the_token_budget():
    ctx = run_stub(scenario="ineffective")
    assert ctx.data["rematch_count"] == 1
    assert ctx.budget.used_attempts > ctx.data["rematch_count"]
    assert ctx.budget.used_tokens > 0
    cleanup()


def test_llm_failure_degrades_to_deterministic_text():
    """TEST 14 - a model outage must not corrupt the run."""
    ctx = run_stub(scenario="success", approval="yes", stub_mode="fail")
    assert ctx.state == State.FINISHED

    explanation = ctx.store.records_of_kind("match_explanation")[0].payload
    assert explanation["source"] == "fallback"
    assert "Ananya" in explanation["text"]
    assert ctx.store.records_of_kind("session")[0].payload["source"] == "fallback"
    # deterministic results survived untouched
    assert ctx.store.records_of_kind("outcome")[0].payload["effective"] is True
    cleanup()


def test_invalid_structured_output_degrades_safely():
    ctx = run_stub(scenario="success", approval="yes", stub_mode="invalid_schema")
    assert ctx.state == State.FINISHED
    assert ctx.store.records_of_kind("session")[0].payload["source"] == "fallback"
    cleanup()


def test_no_llm_mode_runs_the_same_state_machine():
    ctx = run_stub(scenario="success", approval="yes", use_llm=False)
    assert ctx.state == State.FINISHED
    assert ctx.budget.used_attempts == 0
    cleanup()


def test_agent_never_silently_approves():
    """With no human and no scripted answer, the run fails rather than approving."""
    from demo.conceptbridge import flow
    from demo.conceptbridge.main import build_context

    ctx = build_context(RunOptions(stub=True, interactive=False, log=quiet,
                                   runtime=temp_runtime()))
    ctx.data["approval_script"] = []
    ctx = flow.build_machine().run(ctx)

    assert ctx.state == State.FAILED
    assert ctx.store.records_of_kind("failure")
    assert ctx.store.records_of_kind("approval") == []
    cleanup()


def test_model_call_budget_stays_small():
    ctx = run_stub(scenario="success", approval="yes")
    assert ctx.budget.used_attempts <= 3     # 1 explanation + 1 session
    cleanup()


def test_stub_provider_is_the_only_difference_from_live():
    provider = StubProvider()
    ctx = run_stub(scenario="success", approval="yes", provider=provider)
    assert ctx.state == State.FINISHED
    assert len(provider.calls) == 2
    cleanup()
