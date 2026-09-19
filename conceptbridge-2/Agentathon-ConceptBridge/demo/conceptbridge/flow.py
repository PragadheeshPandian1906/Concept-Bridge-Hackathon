from __future__ import annotations

import json
import csv
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from slice.llm import complete

from .evaluation import evaluate_outcome
from .matching import find_candidates
from .profiling import build_profiles, profile_map
from .schema import Approval, MatchCandidate, ProfileUpdate, State
from .session import generate_session


class JsonState:
    def __init__(self, path: str | Path = "runtime/conceptbridge/state.json", records_path: str | Path = "runtime/conceptbridge/records.jsonl"):
        self.path, self.records_path = Path(path), Path(records_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any] | None:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else None

    def save(self, data: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def record(self, run_id: str, state: State, kind: str, payload: Any) -> None:
        with self.records_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": time.time(), "run_id": run_id, "state": state.value, "kind": kind, "payload": payload}, default=str) + "\n")


def _profiles_dict(profiles):
    return {p.student_id: p.model_dump() for p in profiles}


class ConceptBridgeFlow:
    def __init__(self, state_store: JsonState | None = None, call: Callable[..., Any] = complete, settings: Any = None, stub: bool = False):
        self.store, self.call, self.settings, self.stub = state_store or JsonState(), call, settings, stub
        self.data = self.store.load()

    def start(self, quiz: str | Path, mappings: str | Path, run_id: str | None = None,
              followup_quiz: str | Path | None = None) -> dict:
        self.data = {"run_id": run_id or f"cb-{uuid.uuid4().hex[:8]}", "state": State.INPUT.value, "profiles": {}, "original_profiles": {}, "excluded_matches": [], "match_history": [], "approvals": [], "sessions": [], "outcomes": [], "profile_updates": [], "rematch_count": 0, "quiz": str(quiz), "mappings": str(mappings), "followup_quiz": str(followup_quiz) if followup_quiz else None}
        self.store.save(self.data)
        self._record("input", {"quiz": str(quiz)})
        self._transition(State.PROFILING)
        profiles = build_profiles(quiz, mappings)
        self.data["profiles"] = _profiles_dict(profiles)
        self.data["original_profiles"] = _profiles_dict(profiles)
        self._record("student_profile", self.data["profiles"])
        self._transition(State.MATCHING)
        return self.advance()

    def advance(self, approval: bool | None = None, scenario: str = "success",
                observations: list[tuple[str, str, float, float]] | None = None,
                pause_after_session: bool = False) -> dict:
        while True:
            state = State(self.data["state"])
            if state in {State.FINISHED, State.NO_SUITABLE_MATCH, State.FAILED}:
                return self.data
            if state is State.MATCHING:
                profiles = [self._profile(value) for value in self.data["profiles"].values()]
                candidates = find_candidates(profiles, set(self.data["excluded_matches"]))
                if not candidates.items:
                    self._transition(State.NO_SUITABLE_MATCH)
                    return self.data
                candidate = candidates.items[0]
                candidate.rationale = self._explain_candidate(candidate)
                self.data["candidate"] = candidate.model_dump()
                self.data["match_history"].append(candidate.model_dump())
                self._record("match_candidate", candidate.model_dump())
                self._transition(State.WAITING_FOR_APPROVAL)
                if approval is None:
                    return self.data
                continue
            if state is State.WAITING_FOR_APPROVAL:
                accepted = bool(approval)
                approval_record = Approval(match_id=self.data["candidate"]["match_id"], approved=accepted, answered_by="cli")
                self.data["approvals"].append(approval_record.model_dump())
                self._record("approval", approval_record.model_dump())
                if not accepted:
                    self.data["excluded_matches"].append(approval_record.match_id)
                    self._transition(State.MATCHING)
                    return self.data
                self._transition(State.SESSION)
            if State(self.data["state"]) is State.SESSION:
                candidate = MatchCandidate.model_validate(self.data["candidate"])
                plan = generate_session(candidate, self.call, self.settings, self._budget())
                self.data["sessions"].append(plan.model_dump())
                self._record("session", plan.model_dump())
                self._transition(State.EVALUATION)
                if pause_after_session:
                    return self.data
            if State(self.data["state"]) is State.EVALUATION:
                outcome = self._make_outcome(scenario, observations)
                self.data["outcomes"].append(outcome.model_dump())
                self._record("outcome", outcome.model_dump())
                if not outcome.effective:
                    self.data["excluded_matches"].append(outcome.match_id)
                    self.data["rematch_count"] += 1
                    if self.data["rematch_count"] >= 2:
                        self._transition(State.NO_SUITABLE_MATCH)
                        return self.data
                    self._transition(State.MATCHING)
                    scenario, approval = "success", True
                    continue
                self._transition(State.UPDATED_PROFILE)
            if State(self.data["state"]) is State.UPDATED_PROFILE:
                for item in self.data["outcomes"][-1]["outcomes"]:
                    update = ProfileUpdate(student_id=item["student_id"], concept=item["concept"], old_score=item["before_score"], new_score=item["after_score"], gain=item["gain"])
                    self._set_score(update)
                    self.data["profile_updates"].append(update.model_dump())
                    self._record("profile_update", update.model_dump())
                self._transition(State.FINISHED)
                return self.data

    def _make_outcome(self, scenario: str, observations=None):
        candidate = MatchCandidate.model_validate(self.data["candidate"])
        if observations is not None:
            return evaluate_outcome(candidate.match_id, observations)
        a, b = profile_map(self._profile(self.data["profiles"][candidate.student_a])), profile_map(self._profile(self.data["profiles"][candidate.student_b]))
        followup = self._followup_scores(candidate.match_id, scenario)
        observations = []
        for student_id, concepts, scores in ((candidate.student_a, candidate.b_teaches, a), (candidate.student_b, candidate.a_teaches, b)):
            for concept in concepts:
                before = scores[concept]
                after = followup.get((student_id, concept), before + (0.03 if scenario == "ineffective" else 0.40))
                observations.append((student_id, concept, before, min(1.0, after)))
        return evaluate_outcome(candidate.match_id, observations)

    def _followup_scores(self, match_id: str, scenario: str) -> dict[tuple[str, str], float]:
        path = self.data.get("followup_quiz")
        if not path or not Path(path).exists():
            return {}
        column = "ineffective_after" if scenario == "ineffective" else "success_after"
        with Path(path).open(newline="", encoding="utf-8") as handle:
            return {(row["student_id"], row["concept"]): float(row[column])
                    for row in csv.DictReader(handle) if row["match_id"] == match_id}

    def _explain_candidate(self, candidate: MatchCandidate) -> str:
        fallback = candidate.rationale
        try:
            from pathlib import Path
            prompt = (Path(__file__).parent / "prompts" / "match_explain.md").read_text(encoding="utf-8")
            result = self.call(settings=self.settings, budget=self._budget(),
                               messages=[{"role": "system", "content": prompt},
                                         {"role": "user", "content": json.dumps(candidate.model_dump())}],
                               schema=None, step="match_explain")
            return result.strip() if isinstance(result, str) and result.strip() else fallback
        except Exception:
            return fallback

    def _set_score(self, update):
        for item in self.data["profiles"][update.student_id]["concepts"]:
            if item["concept"] == update.concept:
                item["score"] = update.new_score

    def _profile(self, value):
        from .schema import StudentProfile
        return StudentProfile.model_validate(value)

    def _budget(self):
        class LocalBudget:
            def record_tokens(self, _n): pass
            def check_tokens(self): pass
        return LocalBudget()

    def _transition(self, state: State):
        old = State(self.data["state"])
        self.data["state"] = state.value
        self.store.save(self.data)
        self.store.record(self.data["run_id"], state, "state_transition", {"from": old.value, "to": state.value})

    def _record(self, kind, payload):
        self.store.save(self.data)
        self.store.record(self.data["run_id"], State(self.data["state"]), kind, payload)