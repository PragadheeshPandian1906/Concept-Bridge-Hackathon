"""Domain output schemas backed by the reusable agent runtime."""
from pydantic import AliasChoices, BaseModel, Field

from slice.llm import LLMUnavailable, OpenRouterClient


class OpenAnswerGrade(BaseModel):
    score: float = Field(ge=0, le=5)
    normalized_score: float = Field(ge=0, le=1)
    strengths: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)


class SessionRoundContent(BaseModel):
    teacher_id: str = Field(validation_alias=AliasChoices("teacher_id", "teacher"))
    learner_id: str = Field(validation_alias=AliasChoices("learner_id", "learner"))
    concept_id: str = Field(validation_alias=AliasChoices("concept_id", "concept"))
    objective: str
    explanation: str
    example: str
    activity: str
    understanding_check: str


class SessionPlanContent(BaseModel):
    overall_objective: str = Field(validation_alias=AliasChoices("overall_objective", "session_objective", "objective"))
    rounds: list[SessionRoundContent]


class FollowUpQuestion(BaseModel):
    concept_id: str
    prompt: str
    rubric: str = ""
    type: str = "open"


class FollowUpQuestionSet(BaseModel):
    questions: list[FollowUpQuestion] = Field(validation_alias=AliasChoices("questions", "assessments"))
