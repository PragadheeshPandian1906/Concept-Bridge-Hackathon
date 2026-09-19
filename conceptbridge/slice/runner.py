"""Explicit state-machine execution.

The engine knows nothing about the domain. It keeps a current state,
calls the handler registered for that state, records the transition and
moves on. Handlers return the next state name (or ``PAUSE`` to stop and
persist for a later ``resume``).

A hard ``max_steps`` guard means a run can never loop forever, even if a
domain handler is buggy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .budget import Budget
from .config import Config
from .errors import StateMachineError
from .records import RecordKind, make_record
from .store import Store

PAUSE = "__PAUSE__"


@dataclass
class RunContext:
    """Everything a handler may touch."""

    run_id: str
    state: str
    store: Store
    config: Config
    budget: Budget
    data: dict = field(default_factory=dict)
    provider: object = None
    log: Callable[[str], None] = print
    stop_after: str | None = None
    steps: int = 0

    # -- history ----------------------------------------------------
    def record(self, kind: str, payload=None, version: int = 0):
        rec = make_record(self.run_id, self.state, kind, payload, version)
        return self.store.append(rec)

    def versioned_record(self, kind: str, payload=None):
        return self.record(kind, payload, version=self.store.next_version(kind))

    def snapshot(self) -> dict:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "steps": self.steps,
            "budget": self.budget.snapshot(),
            "data": self.data,
        }

    def persist(self) -> None:
        self.store.save_state(self.snapshot())


class StateMachine:
    """Registry of state handlers plus the execution loop."""

    def __init__(self, initial: str, terminal: set[str], max_steps: int = 60):
        self.initial = initial
        self.terminal = set(terminal)
        self.max_steps = max_steps
        self.handlers: dict[str, Callable[[RunContext], str]] = {}

    def handler(self, state: str):
        def decorator(fn):
            self.handlers[state] = fn
            return fn
        return decorator

    def register(self, state: str, fn) -> None:
        self.handlers[state] = fn

    def run(self, ctx: RunContext) -> RunContext:
        if not ctx.state:
            ctx.state = self.initial
        ctx.persist()

        while ctx.state not in self.terminal:
            if ctx.steps >= self.max_steps:
                self._transition(ctx, "FAILED", reason="max_steps_exceeded")
                ctx.record(RecordKind.FAILURE,
                           {"reason": "max steps exceeded", "state": ctx.state})
                break

            handler = self.handlers.get(ctx.state)
            if handler is None:
                raise StateMachineError(f"no handler registered for state {ctx.state!r}")

            ctx.steps += 1
            next_state = handler(ctx)

            if next_state == PAUSE:
                ctx.persist()
                return ctx
            if next_state is None:
                raise StateMachineError(
                    f"handler for {ctx.state!r} returned no next state"
                )
            if next_state != ctx.state:
                self._transition(ctx, next_state)
            ctx.persist()

            if ctx.stop_after and ctx.stop_after == ctx.state:
                ctx.log(f"\n[paused after {ctx.state}] state saved; use `resume` to continue")
                return ctx

        ctx.persist()
        return ctx

    # -- internals --------------------------------------------------
    @staticmethod
    def _transition(ctx: RunContext, next_state: str, reason: str | None = None) -> None:
        payload = {"from": ctx.state, "to": next_state}
        if reason:
            payload["reason"] = reason
        ctx.record(RecordKind.STATE_TRANSITION, payload)
        ctx.state = next_state
