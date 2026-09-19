"""Drop and recreate all tables, and clear artifacts."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.conceptbridge.persistence.database import reset_db  # noqa: E402
from slice.config import get_settings  # noqa: E402

if __name__ == "__main__":
    reset_db()
    shutil.rmtree(get_settings().artifacts_dir, ignore_errors=True)
    print("database reset")
