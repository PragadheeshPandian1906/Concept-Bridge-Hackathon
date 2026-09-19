"""Durable state + append-only history.

Two files per run directory:

    state.json      the current, resumable snapshot (overwritten atomically)
    records.jsonl   append-only history (never rewritten)

The snapshot exists so a run can resume. The history exists so a run can
be replayed and audited. Losing the snapshot never loses the history.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .records import Record


class Store:
    """File-backed store for one agent workspace."""

    def __init__(self, root: str | Path = "runtime/conceptbridge"):
        self.root = Path(root)
        self.state_path = self.root / "state.json"
        self.records_path = self.root / "records.jsonl"
        self.root.mkdir(parents=True, exist_ok=True)

    # -- append-only history ---------------------------------------
    def append(self, record: Record) -> Record:
        line = json.dumps(record.model_dump(), ensure_ascii=False)
        with self.records_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return record

    def read_records(self) -> list[Record]:
        if not self.records_path.exists():
            return []
        out: list[Record] = []
        for line in self.records_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(Record.model_validate(json.loads(line)))
        return out

    def records_of_kind(self, kind: str) -> list[Record]:
        return [r for r in self.read_records() if r.kind == kind]

    def next_version(self, kind: str) -> int:
        """Version numbers are per-kind and strictly increasing."""
        return len(self.records_of_kind(kind)) + 1

    # -- resumable snapshot ----------------------------------------
    def save_state(self, state: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, self.state_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def load_state(self) -> dict | None:
        if not self.state_path.exists():
            return None
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def exists(self) -> bool:
        return self.state_path.exists()

    # -- lifecycle --------------------------------------------------
    def reset(self) -> None:
        for path in (self.state_path, self.records_path):
            if path.exists():
                path.unlink()
