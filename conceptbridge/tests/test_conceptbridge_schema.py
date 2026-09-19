"""Schema and structured-output tests (covers spec TEST 12)."""

from helpers import assert_raises, profile

from slice.compat import ValidationError
from slice.errors import SchemaError
from slice.structured import complete_structured, extract_json, schema_hint
from slice.config import Config
from slice.budget import Budget
from demo.conceptbridge.schema import (Approval, MatchCandidate, SessionPlan,
                                       StudentProfile)
from demo.conceptbridge.stub import StubProvider


def _config():
    return Config(api_key="test-key", model="m1", fallback_model="m2",
                  escalation_model="m3")


def test_models_round_trip():
    original = profile("S1", "Ananya", Arrays=0.85, Recursion=0.90)
    restored = StudentProfile.model_validate(original.model_dump())
    assert restored.student_id == "S1"
    assert restored.score_for("Recursion") == 0.90
    assert restored.as_dict() == {"Arrays": 0.85, "Recursion": 0.90}


def test_missing_required_field_is_rejected():
    assert_raises(ValidationError, Approval, match_id="S1|S2", approved=True)


def test_wrong_type_is_rejected():
    assert_raises(ValidationError, Approval,
                  match_id="S1|S2", approved="definitely", answered_by="cli")


def test_profile_update_is_immutable():
    original = profile("S1", "Ananya", SQL=0.35)
    updated = original.with_score("SQL", 0.75)
    assert original.score_for("SQL") == 0.35
    assert updated.score_for("SQL") == 0.75


def test_extract_json_handles_fenced_and_noisy_output():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure!\n{"a": {"b": 2}}\nHope that helps.') == {"a": {"b": 2}}
    assert_raises(SchemaError, extract_json, "no json at all")


def test_schema_hint_lists_every_field():
    hint = schema_hint(MatchCandidate)
    for field in ("match_id", "compatibility_score", "a_teaches", "rationale"):
        assert f'"{field}"' in hint


def test_invalid_llm_output_fails_safely():
    """TEST 12 - invalid structured output is repaired, then raises."""
    provider = StubProvider(mode="invalid_schema")
    assert_raises(
        SchemaError, complete_structured,
        "make a session", SessionPlan, config=_config(),
        budget=Budget(max_tokens=99999, max_attempts=9), provider=provider,
    )
    # one original attempt + one repair attempt, and nothing was fabricated
    assert len(provider.calls) == 2


def test_non_json_llm_output_fails_safely():
    provider = StubProvider(mode="garbage")
    assert_raises(
        SchemaError, complete_structured,
        "make a session", SessionPlan, config=_config(),
        budget=Budget(max_tokens=99999, max_attempts=9), provider=provider,
    )
