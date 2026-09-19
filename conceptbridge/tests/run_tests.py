#!/usr/bin/env python3
"""Run the whole suite without pytest.

    python tests/run_tests.py

The tests are ordinary pytest test functions with no fixtures, so
``pytest -q`` works too. This runner exists so the suite still runs on a
machine with no packages installed at all.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

MODULES = [
    "test_conceptbridge_schema",
    "test_conceptbridge_profiling",
    "test_conceptbridge_matching",
    "test_conceptbridge_evaluation",
    "test_conceptbridge_flow",
    "test_conceptbridge_persistence",
    "test_conceptbridge_adversarial",
]


def main() -> int:
    passed, failures = 0, []
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        print(f"\n{module_name}")
        for name in sorted(vars(module)):
            fn = getattr(module, name)
            if not (name.startswith("test_") and callable(fn)):
                continue
            try:
                fn()
            except Exception:
                failures.append((module_name, name, traceback.format_exc()))
                print(f"  FAIL  {name}")
            else:
                passed += 1
                print(f"  ok    {name}")

    print("\n" + "=" * 58)
    for module_name, name, trace in failures:
        print(f"\nFAILED {module_name}::{name}\n{trace}")
    print(f"{passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
