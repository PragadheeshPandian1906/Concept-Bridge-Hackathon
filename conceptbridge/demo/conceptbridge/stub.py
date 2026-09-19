"""Deterministic stub provider.

Stub mode is NOT a second pipeline. It swaps exactly one object - the
provider handed to ``slice.llm.complete`` - so every state, record,
schema check, budget charge and transition is identical to live mode.

    python scripts/conceptbridge.py run --stub

``mode`` lets tests exercise failure paths:

    ok              well-formed JSON for every step
    invalid_schema  syntactically fine but schema-invalid output
    garbage         not JSON at all
    fail            the provider itself raises (model/OpenRouter outage)
"""

from __future__ import annotations

import json
import re

from slice.errors import ProviderError
from slice.llm import LLMResult, estimate_tokens


def _field(prompt: str, label: str, default: str = "") -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", prompt, re.MULTILINE)
    return match.group(1).strip() if match else default


def _teaches(prompt: str, marker: str) -> list[str]:
    match = re.search(rf"will teach.*?:\s*(.+)$", marker, re.MULTILINE)
    if match:
        return [c.strip() for c in match.group(1).split(",") if c.strip()]
    return []


class StubProvider:
    """Offline, deterministic stand-in for OpenRouter."""

    name = "stub"

    def __init__(self, mode: str = "ok"):
        self.mode = mode
        self.calls: list[dict] = []

    # -- provider protocol -----------------------------------------
    def complete(self, messages: list[dict], model: str, config) -> LLMResult:
        prompt = "\n".join(m.get("content", "") for m in messages)
        self.calls.append({"model": model, "chars": len(prompt)})

        if self.mode == "fail":
            raise ProviderError("stub provider: simulated model failure")

        text = self._respond(prompt)
        return LLMResult(
            text=text,
            model=f"stub/{model}",
            prompt_tokens=estimate_tokens(prompt),
            completion_tokens=estimate_tokens(text),
            provider=self.name,
        )

    # -- canned responses ------------------------------------------
    def _respond(self, prompt: str) -> str:
        if self.mode == "garbage":
            return "Sure! Here is the answer you asked for, in prose."

        is_session = "learning_objectives" in prompt
        is_explain = "a_teaches_reason" in prompt
        match_id = _field(prompt, "Match id", "unknown")

        if self.mode == "invalid_schema":
            # valid JSON, wrong shape: exercises repair + SchemaError
            return json.dumps({"match_id": 12345, "unexpected": True})

        if is_explain:
            payload = {
                "match_id": match_id,
                "summary": ("These two learners are complementary: each one is strong "
                            "exactly where the other still has room to grow, so the "
                            "pairing gives both of them something to teach and "
                            "something to learn."),
                "a_teaches_reason": ("Student A scored well above the strength "
                                     "threshold on the listed concepts, where "
                                     "Student B is still below the gap threshold."),
                "b_teaches_reason": ("Student B scored well above the strength "
                                     "threshold on the listed concepts, where "
                                     "Student A is still below the gap threshold."),
            }
            return json.dumps(payload, indent=2)

        if is_session:
            a_name = _field(prompt, "Match id") and ""
            a_primary = self._primary(prompt, first=True)
            b_primary = self._primary(prompt, first=False)
            payload = {
                "match_id": match_id,
                "learning_objectives": [
                    f"Explain the core idea of {a_primary} in your own words.",
                    f"Explain the core idea of {b_primary} in your own words.",
                    f"Work one problem on {a_primary} without help.",
                    f"Work one problem on {b_primary} without help.",
                ],
                "teaching_directions": self._directions(prompt),
                "teaching_prompts": [
                    f"Start with a small worked example of {a_primary}.",
                    f"Ask your partner to point out the tricky step in {b_primary}.",
                    "Finish by swapping one short problem each.",
                ],
                "shared_challenge": (f"Solve one task that needs {a_primary} and one "
                                     f"that needs {b_primary}, then compare how you "
                                     f"each approached them."),
                "follow_up_questions": [
                    f"A short question on {a_primary}.",
                    f"A short question on {b_primary}.",
                    "A question that combines both concepts.",
                ],
            }
            return json.dumps(payload, indent=2)

        # profile interpretation / anything else
        return json.dumps({
            "student_id": _field(prompt, "Student", "unknown").split(" ")[0],
            "summary": ("This learner is stronger on some concepts than others; "
                        "the scores shown were computed from quiz evidence."),
        }, indent=2)

    @staticmethod
    def _primary(prompt: str, first: bool) -> str:
        found = re.findall(r"^Focus concept for this direction:\s*(.+)$",
                           prompt, re.MULTILINE)
        if not found:
            return "the focus concept"
        return found[0].strip() if first else found[-1].strip()

    @staticmethod
    def _directions(prompt: str) -> list[str]:
        found = re.findall(r"^(\S.*? will teach .+)$", prompt, re.MULTILINE)
        out = []
        for line in found:
            line = line.strip()
            who, _, what = line.partition(":")
            who = who.replace(" will teach ", " -> ")
            out.append(f"{who.strip()}: {what.strip()}")
        return out or ["Partner A -> Partner B", "Partner B -> Partner A"]


def make_provider(stub: bool, mode: str = "ok"):
    """Return the stub provider, or None to use the real OpenRouter one."""
    return StubProvider(mode=mode) if stub else None
