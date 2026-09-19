import pytest

from demo.conceptbridge.state import (
    InvalidTransition,
    RunState,
    create_run,
    history,
    load_state,
    transition,
)


def test_happy_path_transitions(db):
    run_id = create_run(db).run_id
    for state in [
        RunState.PROFILING,
        RunState.MATCHING,
        RunState.WAITING_FOR_APPROVAL,
        RunState.SESSION,
        RunState.EVALUATION,
        RunState.UPDATED_PROFILE,
        RunState.FINISHED,
    ]:
        transition(db, run_id, state)
    assert load_state(db, run_id) is RunState.FINISHED
    assert len(history(db, run_id)) == 8  # creation + 7 transitions


def test_invalid_transition_is_rejected(db):
    run_id = create_run(db).run_id
    with pytest.raises(InvalidTransition):
        transition(db, run_id, RunState.SESSION)


def test_rejection_loops_back_to_matching(db):
    run_id = create_run(db).run_id
    transition(db, run_id, RunState.PROFILING)
    transition(db, run_id, RunState.MATCHING)
    transition(db, run_id, RunState.WAITING_FOR_APPROVAL)
    transition(db, run_id, RunState.MATCHING, "rejected")
    assert load_state(db, run_id) is RunState.MATCHING


def test_state_survives_a_new_session(db):
    from demo.conceptbridge.persistence.database import SessionLocal

    run_id = create_run(db).run_id
    transition(db, run_id, RunState.PROFILING)
    fresh = SessionLocal()
    assert load_state(fresh, run_id) is RunState.PROFILING  # resume after restart
    fresh.close()
