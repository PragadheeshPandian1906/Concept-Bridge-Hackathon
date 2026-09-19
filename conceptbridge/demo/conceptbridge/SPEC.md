# ConceptBridge — SPEC

One-quiz reciprocal peer-match agent, built on the reusable `slice/` engine.

## 1. Problem

A single class quiz tells us who is strong and who is stuck, per concept.
Most systems stop there and produce a tutor list. ConceptBridge instead
looks for **reciprocal** pairs — two learners who can each teach the other
something — proposes one to a teacher, runs a peer session, measures whether
learning actually happened, and **changes its mind when it did not**.

## 2. Input

| File | Contents |
|---|---|
| `data/quiz.csv` | `student_id, student_name, question_id, score, response_text` — 6 students × 12 questions, partial credit in `[0,1]` |
| `data/question_concepts.csv` | `question_id, concept` — 12 questions → 6 concepts |
| `data/followup_quiz.csv` | `scenario, match_key, student_id, question_id, concept, score` — post-session evidence |
| `data/sample_students.csv` | expected concept scores; the profiling tests assert against this file |

Concepts: Arrays, Recursion, Trees, Functions, SQL Joins, Normalization.

`response_text` is **untrusted data**. Two rows contain a deliberate prompt
injection, used by `tests/test_conceptbridge_adversarial.py`.

## 3. Output

A terminal run plus two durable files:

```
runtime/conceptbridge/state.json      resumable snapshot
runtime/conceptbridge/records.jsonl   append-only history
```

## 4. State machine

```
INPUT → PROFILING → MATCHING → WAITING_FOR_APPROVAL
                       ↑                │
                       │ reject         │ approve
                       │                ▼
                       │             SESSION
                       │                │
                       │            EVALUATION
                       │           │           │
                       │ ineffective           effective
                       └───────────┘           │
                                               ▼
                                        UPDATED_PROFILE → FINISHED

MATCHING → NO_SUITABLE_MATCH      (terminal)
any state → FAILED                (terminal)
```

Terminal: `FINISHED`, `NO_SUITABLE_MATCH`, `FAILED`.
Handlers are registered explicitly in `flow.build_machine()`; the engine
(`slice/runner.py`) records every transition and enforces a hard
`max_steps` guard so a run can never loop forever.

## 5. Agentic decisions

| Decision | Where | Evidence in the record log |
|---|---|---|
| which pair to propose | `matching.generate_candidates` | `match_candidate` |
| wait for a human | `flow.handle_waiting_for_approval` | `approval` |
| react to rejection | same | `state_transition WAITING_FOR_APPROVAL → MATCHING` |
| did the session work | `evaluation.evaluate_match` | `outcome` |
| try a different pair | `flow.handle_evaluation` | `state_transition EVALUATION → MATCHING` |
| stop trying | `MAX_REMATCH_ATTEMPTS` | `NO_SUITABLE_MATCH` |

The backward transitions are the proof that this is an agent and not a
pipeline.

## 6. Data model

All in `schema.py`, all typed: `ConceptScore`, `StudentProfile`,
`MatchCandidate`, `MatchCandidates`, `MatchExplanation`, `Approval`,
`SessionPlan`, `LearningOutcome`, `SessionOutcome`, `ProfileUpdate`,
`Failure`, `RunInput`. No step passes free-form prose to another step.

## 7. Deterministic logic

**Profiling** (`profiling.py`)

```
concept_score = mean(question_scores_for_concept)      clamped to [0,1]
```

**Thresholds** (`matching.py`)

```
STRENGTH_THRESHOLD = 0.70      # may teach
GAP_THRESHOLD      = 0.60      # has a useful gap
```

**Reciprocal eligibility** — A teaches B on concept `c` when
`A[c] ≥ 0.70 and B[c] < 0.60`. A pair is a candidate only when **both**
directions teach at least one concept.

**Compatibility**

```
a_to_b        = Σ (A[c] − B[c]) for c in a_teaches
b_to_a        = Σ (B[c] − A[c]) for c in b_teaches
total         = a_to_b + b_to_a
balance       = 1 − |a_to_b − b_to_a| / total
compatibility = min(1, total / 2.5) × (0.5 + 0.5 × balance)
```

`IDEAL_TOTAL_GAP = 2.5` is the point where extra gap stops adding value.
Candidates sort by `(−compatibility, match_id)` — fully deterministic.

**Evaluation** (`evaluation.py`)

```
gain = after − before
LEARNING_GAIN_THRESHOLD = 0.10
effective = both directions clear the threshold on their focus concept
```

The focus concept of a direction is the largest measured gap
(`matching.primary_concept`), which is what the follow-up quiz targets.

## 8. LLM responsibilities

Allowed: match explanation (1 call), session generation (1 call).
A normal run costs **2 model calls**.

Forbidden: quiz scoring, concept aggregation, compatibility, learning
gain, threshold comparison, state transitions.

All calls go through `slice.llm.complete` → OpenRouter, with typed output
via `slice.structured.complete_structured` (schema repair, fallback
models, budget). Every model output has a deterministic fallback, so an
outage changes the wording and nothing else.

## 9. Persistence

`slice/store.py`. `state.json` is the resumable snapshot; `records.jsonl`
is append-only and never rewritten. Record kinds: `input`,
`student_profile`, `match_candidate`, `match_explanation`, `approval`,
`session`, `outcome`, `profile_update`, `failure`, `state_transition`,
`llm_call`, `note`. Each record carries `timestamp, run_id, state, kind,
version, payload`.

`original_profiles` is kept alongside the live profiles, so a profile
update never destroys the pre-session picture.

## 10. Failure paths

| Failure | Handling |
|---|---|
| malformed / missing CSV | `ProfilingError` → `FAILED` + `failure` record |
| unmapped question | `ProfilingError` → `FAILED` |
| invalid structured output | one schema-repair attempt, then `SchemaError` → deterministic fallback |
| model failure | next model in the chain, then fallback text |
| OpenRouter unreachable | `ProviderError` → fallback text, run continues |
| token / attempt exhaustion | `BudgetExceeded` → fallback text, run continues |
| no approval available | `FAILED` — the agent never auto-approves |
| max re-matches | `NO_SUITABLE_MATCH` |
| no reciprocal pair | `NO_SUITABLE_MATCH` |
| runaway loop | `max_steps` guard → `FAILED` |

Nothing is ever fabricated to keep a run alive.

## 11. Test scenarios

```
run --stub --scenario success       approve → effective → profile update → FINISHED
run --stub --scenario reject        S1|S2 rejected → S1|S3 proposed → FINISHED
run --stub --scenario ineffective   S1|S2 gain +0.02 → re-match → S1|S3 → FINISHED
run --stub --scenario no-match      roster with no reciprocity → NO_SUITABLE_MATCH
run --stub --approval no            rejected until the domain limit → NO_SUITABLE_MATCH
```

55 tests across 7 modules cover spec TEST 1–14.

## 12. Intentionally not implemented

No frontend, no REST/Express/Flask routes, no auth, no database server, no
deployment, no LMS integration, no knowledge graph, no automatic taxonomy,
no reinforcement learning, no multi-agent orchestration. Group sessions,
multi-course profiles and scheduling are out of scope for this pilot.
