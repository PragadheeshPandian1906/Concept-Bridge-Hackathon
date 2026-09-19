#!/usr/bin/env python3
"""ConceptBridge CLI.

    python scripts/conceptbridge.py run --stub
    python scripts/conceptbridge.py run --stub --approval yes
    python scripts/conceptbridge.py run --stub --scenario ineffective
    python scripts/conceptbridge.py run                 # live OpenRouter
    python scripts/conceptbridge.py resume
    python scripts/conceptbridge.py inspect
    python scripts/conceptbridge.py reset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.conceptbridge.main import (DEFAULT_RUNTIME, RunOptions, SCENARIOS,
                                     inspect, reset, resume, run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="conceptbridge", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--stub", action="store_true",
                       help="use the deterministic offline provider (no API key)")
        p.add_argument("--no-llm", action="store_true",
                       help="skip model calls entirely; use deterministic text")
        p.add_argument("--approval", default=None,
                       help="non-interactive approval answers, e.g. yes | no | no,yes")
        p.add_argument("--runtime", default=str(DEFAULT_RUNTIME),
                       help="where state.json and records.jsonl live")
        p.add_argument("--stub-mode", default="ok",
                       choices=["ok", "invalid_schema", "garbage", "fail"],
                       help="stub failure injection (testing)")

    run_p = sub.add_parser("run", help="start a fresh run")
    common(run_p)
    run_p.add_argument("--scenario", default="success", choices=sorted(SCENARIOS))
    run_p.add_argument("--stop-after", default=None,
                       help="pause and persist once this state is reached")

    resume_p = sub.add_parser("resume", help="continue the persisted run")
    common(resume_p)

    inspect_p = sub.add_parser("inspect", help="show persisted state and history")
    inspect_p.add_argument("--runtime", default=str(DEFAULT_RUNTIME))

    reset_p = sub.add_parser("reset", help="clear persisted state and history")
    reset_p.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "inspect":
        inspect(args.runtime)
        return 0
    if args.command == "reset":
        reset(args.runtime)
        return 0

    options = RunOptions(
        stub=args.stub,
        stub_mode=args.stub_mode,
        approval=args.approval,
        interactive=args.approval is None,
        use_llm=not args.no_llm,
        runtime=args.runtime,
    )
    if args.command == "run":
        options.scenario = args.scenario
        options.stop_after = args.stop_after
        ctx = run(options)
    else:
        ctx = resume(options)

    return 0 if ctx.state in ("FINISHED", "NO_SUITABLE_MATCH") else 1


if __name__ == "__main__":
    raise SystemExit(main())
