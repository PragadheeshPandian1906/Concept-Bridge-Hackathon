from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CONCEPTBRIDGE_", extra="ignore")
    database_path: str = "runtime/conceptbridge.db"
    min_group_size: int = 2
    max_group_size: int = 5
    strength_threshold: float = 0.70
    gap_threshold: float = 0.60
    min_transfer_gap: float = 0.20
    effective_gain_threshold: float = 0.20
    max_teaching_load: int = 3
    previous_match_penalty: float = 0.08
    ineffective_match_penalty: float = 0.15
    demo_mode: bool = False
    strict_llm: bool = True
    openrouter_api_key: str | None = Field(default=None, validation_alias=AliasChoices("OPENROUTER_API_KEY", "CONCEPTBRIDGE_OPENROUTER_API_KEY"))
    llm_model: str = "openai/gpt-4.1-mini"
    llm_fallback_model: str = "openai/gpt-4.1-mini"
    llm_timeout: float = 20.0
    llm_max_tokens: int = 1200
    weight_coverage: float = 0.30
    weight_reciprocity: float = 0.10
    weight_transfer_strength: float = 0.30
    weight_fairness: float = 0.15
    weight_effectiveness: float = 0.15

    def ensure_directories(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
