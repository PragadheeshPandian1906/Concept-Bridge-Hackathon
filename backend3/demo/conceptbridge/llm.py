<<<<<<< HEAD:conceptbridge/demo/conceptbridge/llm.py
"""Single bounded OpenRouter gateway. Domain logic never calls the provider directly."""
import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, Field

from .config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def structured(self, system: str, user: str, output_model: type[T]) -> T:
        """Request validated JSON, retry once with the configured fallback model."""
        if self.settings.demo_mode or not self.settings.openrouter_api_key:
            raise LLMUnavailable("LLM is unavailable in demo mode or without OPENROUTER_API_KEY")
        errors: list[str] = []
        for model in dict.fromkeys([self.settings.llm_model, self.settings.llm_fallback_model]):
            try:
                response = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openrouter_api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "response_format": {"type": "json_object"}, "max_tokens": self.settings.llm_max_tokens},
                    timeout=self.settings.llm_timeout,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return output_model.model_validate(json.loads(content))
            except Exception as exc:  # provider/network/schema failures are contained at this boundary
                errors.append(str(exc))
        raise LLMUnavailable("OpenRouter structured call failed: " + " | ".join(errors))
=======
"""Domain output schemas backed by the reusable agent runtime."""
from pydantic import AliasChoices, BaseModel, Field

from slice.llm import LLMUnavailable, OpenRouterClient
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/llm.py


class OpenAnswerGrade(BaseModel):
    score: float = Field(ge=0, le=5)
    normalized_score: float = Field(ge=0, le=1)
    strengths: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)


class SessionRoundContent(BaseModel):
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/llm.py
    teacher_id: str
    learner_id: str
    concept_id: str
=======
    teacher_id: str = Field(validation_alias=AliasChoices("teacher_id", "teacher"))
    learner_id: str = Field(validation_alias=AliasChoices("learner_id", "learner"))
    concept_id: str = Field(validation_alias=AliasChoices("concept_id", "concept"))
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/llm.py
    objective: str
    explanation: str
    example: str
    activity: str
    understanding_check: str


class SessionPlanContent(BaseModel):
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/llm.py
    overall_objective: str
=======
    overall_objective: str = Field(validation_alias=AliasChoices("overall_objective", "session_objective", "objective"))
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/llm.py
    rounds: list[SessionRoundContent]


class FollowUpQuestion(BaseModel):
    concept_id: str
    prompt: str
    rubric: str = ""
    type: str = "open"


class FollowUpQuestionSet(BaseModel):
<<<<<<< HEAD:conceptbridge/demo/conceptbridge/llm.py
    questions: list[FollowUpQuestion]
=======
    questions: list[FollowUpQuestion] = Field(validation_alias=AliasChoices("questions", "assessments"))
>>>>>>> ea01724 (working final backend):backend3/demo/conceptbridge/llm.py
