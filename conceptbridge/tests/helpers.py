"""Shared helpers. Deliberately plain functions so the suite runs under
pytest *and* under ``python tests/run_tests.py`` with no dependencies."""

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.conceptbridge.main import RunOptions, run  # noqa: E402
from demo.conceptbridge.schema import ConceptScore, StudentProfile  # noqa: E402

_TEMP_DIRS = []


def temp_runtime() -> Path:
    path = Path(tempfile.mkdtemp(prefix="cb-test-"))
    _TEMP_DIRS.append(path)
    return path


def cleanup():
    while _TEMP_DIRS:
        shutil.rmtree(_TEMP_DIRS.pop(), ignore_errors=True)


def quiet(_msg=""):
    pass


def profile(student_id: str, name: str, **scores) -> StudentProfile:
    """profile("A", "Alice", Recursion=0.9, SQL=0.3)"""
    return StudentProfile(
        student_id=student_id,
        student_name=name,
        concepts=[ConceptScore(concept=k.replace("_", " "), score=v)
                  for k, v in scores.items()],
    )


def run_stub(**kwargs):
    """Run the agent offline with output suppressed."""
    options = RunOptions(stub=True, interactive=False, log=quiet,
                         runtime=temp_runtime(), **kwargs)
    return run(options)


def assert_raises(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc_type:
        return True
    except Exception as other:  # pragma: no cover - diagnostic
        raise AssertionError(
            f"expected {exc_type.__name__}, got {type(other).__name__}: {other}"
        )
    raise AssertionError(f"expected {exc_type.__name__}, nothing was raised")


def kinds(store):
    return [r.kind for r in store.read_records()]


def transitions(store):
    return [(r.payload["from"], r.payload["to"])
            for r in store.read_records() if r.kind == "state_transition"]
