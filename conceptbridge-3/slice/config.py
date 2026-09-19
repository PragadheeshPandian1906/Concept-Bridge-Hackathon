"""Central configuration for the generic agent engine."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    model: str
    fallback_model: str
    demo_mode: bool
    timeout: int
    max_tokens: int
    database_url: str
    artifacts_dir: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    demo = _bool("DEMO_MODE", True)
    if not key:
        # No key: the whole system still has to work, so force the stub path.
        demo = True
    return Settings(
        openrouter_api_key=key,
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        fallback_model=os.getenv("OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.1-8b-instruct"),
        demo_mode=demo,
        timeout=_int("LLM_TIMEOUT", 60),
        max_tokens=_int("LLM_MAX_TOKENS", 2000),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./runtime/conceptbridge.db"),
        artifacts_dir=os.getenv("ARTIFACTS_DIR", "./runtime/artifacts"),
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()
