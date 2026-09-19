"""Persistence and replay tests (covers spec TEST 10, TEST 11)."""

from helpers import cleanup, kinds, quiet, temp_runtime

from slice.store import Store
from demo.conceptbridge.main import RunOptions, resume, run
from demo.conceptbridge.schema import State


def test_state_survives_a_restart():
    """TEST 10 - stop after profiling, start a new process-equivalent, resume."""
    runtime = temp_runtime()
    first = run(RunOptions(stub=True, interactive=False, approval="yes",
                           log=quiet, runtime=runtime, stop_after=State.MATCHING))
    assert first.state == State.MATCHING
    assert len(first.data["profiles"]) == 6

    # a brand new Store, as a fresh process would build
    reopened = Store(runtime)
    snapshot = reopened.load_state()
    assert snapshot["state"] == State.MATCHING
    assert snapshot["run_id"] == first.run_id
    assert len(snapshot["data"]["profiles"]) == 6

    second = resume(RunOptions(stub=True, interactive=False, approval="yes",
                               log=quiet, runtime=runtime))
    assert second.run_id == first.run_id
    assert second.state == State.FINISHED
    cleanup()


def test_profile_update_persists_across_a_restart():
    """TEST 11 - Ananya's SQL Joins score stays updated after a restart."""
    runtime = temp_runtime()
    ctx = run(RunOptions(stub=True, interactive=False, approval="yes",
                         scenario="success", log=quiet, runtime=runtime))
    assert ctx.state == State.FINISHED

    snapshot = Store(runtime).load_state()
    profiles = {p["student_id"]: p for p in snapshot["data"]["profiles"]}
    sql = {c["concept"]: c["score"] for c in profiles["S1"]["concepts"]}["SQL Joins"]
    assert sql == 0.75

    original = {c["concept"]: c["score"]
                for c in snapshot["data"]["original_profiles"][0]["concepts"]}
    assert original["SQL Joins"] == 0.35      # history is not rewritten
    cleanup()


def test_history_is_append_only_and_ordered():
    runtime = temp_runtime()
    ctx = run(RunOptions(stub=True, interactive=False, scenario="success",
                         log=quiet, runtime=runtime))
    order = [k for k in kinds(ctx.store)
             if k in ("input", "student_profile", "match_candidate", "approval",
                      "session", "outcome", "profile_update")]
    assert order[0] == "input"
    assert order.index("match_candidate") < order.index("approval")
    assert order.index("approval") < order.index("session")
    assert order.index("session") < order.index("outcome")
    assert order.index("outcome") < order.index("profile_update")
    cleanup()


def test_records_are_versioned_per_kind():
    runtime = temp_runtime()
    ctx = run(RunOptions(stub=True, interactive=False, scenario="ineffective",
                         log=quiet, runtime=runtime))
    versions = [r.version for r in ctx.store.records_of_kind("match_candidate")]
    assert versions == [1, 2]
    cleanup()


def test_a_new_run_does_not_inherit_old_state():
    runtime = temp_runtime()
    run(RunOptions(stub=True, interactive=False, scenario="success",
                   log=quiet, runtime=runtime))
    second = run(RunOptions(stub=True, interactive=False, scenario="success",
                            log=quiet, runtime=runtime))
    assert second.store.records_of_kind("input")[0].run_id == second.run_id
    assert len(second.store.records_of_kind("input")) == 1
    cleanup()


def test_run_is_replayable_from_records_alone():
    runtime = temp_runtime()
    ctx = run(RunOptions(stub=True, interactive=False, scenario="ineffective",
                         log=quiet, runtime=runtime))
    replay = [f"{r.kind}" for r in Store(runtime).read_records()]
    assert replay.count("match_candidate") == 2
    assert replay.count("outcome") == 2
    assert "profile_update" in replay
    assert ctx.state == State.FINISHED
    cleanup()
