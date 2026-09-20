import pytest
from pydantic import BaseModel

from demo.conceptbridge.config import Settings
from demo.conceptbridge.llm import FollowUpQuestionSet, SessionPlanContent
from slice.llm import LLMUnavailable, OpenRouterClient


class DemoOutput(BaseModel):
    answer: str


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": '{"answer":"connected"}'}}]}


def test_configured_runtime_calls_openrouter(monkeypatch, tmp_path):
    calls = []

    def fake_post(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return FakeResponse()

    monkeypatch.setattr("slice.llm.httpx.post", fake_post)
    settings = Settings(
        database_path=str(tmp_path / "test.db"),
        demo_mode=False,
        openrouter_api_key="test-key",
        llm_model="test/model",
        llm_fallback_model="fallback/model",
    )

    result = OpenRouterClient(settings).structured("system", "user", DemoOutput)

    assert result.answer == "connected"
    assert calls[0][0] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls[0][1]["json"]["model"] == "test/model"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-key"


def test_demo_mode_blocks_provider_call(monkeypatch, tmp_path):
    monkeypatch.setattr("slice.llm.httpx.post", lambda *args, **kwargs: pytest.fail("provider must not be called"))
    settings = Settings(database_path=str(tmp_path / "test.db"), demo_mode=True, openrouter_api_key="test-key")

    with pytest.raises(LLMUnavailable, match="disabled"):
        OpenRouterClient(settings).structured("system", "user", DemoOutput)


def test_session_plan_accepts_equivalent_provider_field_names():
    plan = SessionPlanContent.model_validate(
        {
            "session_objective": "Build confidence with recursion",
            "session_duration_minutes": 45,
            "rounds": [
                {
                    "round_number": 1,
                    "teacher": "A",
                    "learner": "B",
                    "concept": "recursion",
                    "objective": "Identify the base case",
                    "explanation": "Explain the stopping condition",
                    "example": "Factorial",
                    "activity": "Trace a recursive call",
                    "understanding_check": "Explain why the base case is necessary",
                }
            ],
        }
    )

    assert plan.overall_objective == "Build confidence with recursion"
    assert plan.rounds[0].teacher_id == "A"
    assert plan.rounds[0].learner_id == "B"
    assert plan.rounds[0].concept_id == "recursion"


def test_follow_up_questions_accept_assessments_response_key():
    result = FollowUpQuestionSet.model_validate(
        {
            "assessments": [
                {
                    "concept_id": "recursion",
                    "prompt": "Explain why the base case prevents infinite recursion.",
                    "rubric": "Identifies termination correctly.",
                    "type": "open",
                }
            ]
        }
    )

    assert result.questions[0].concept_id == "recursion"