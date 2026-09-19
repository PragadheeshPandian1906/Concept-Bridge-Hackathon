"""Optional JSON artifacts for debugging/demo. SQLite stays the source of truth."""
from __future__ import annotations

import json
from pathlib import Path

from slice.config import get_settings


def save(run_id: str, name: str, payload: dict) -> str:
    directory = Path(get_settings().artifacts_dir) / run_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return str(path)
