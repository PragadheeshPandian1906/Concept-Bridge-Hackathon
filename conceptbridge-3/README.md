# ConceptBridge

**From concept gaps to complementary connections.**

ConceptBridge is an agentic peer-learning system. It scores quiz performance at the
*concept* level, builds a directed knowledge-transfer graph between students, forms
complementary pairs/groups, generates a peer-learning session, measures whether learning
actually happened, updates the learner profiles and then changes the graph that future
matchmaking runs on.

The loop it demonstrates:

```
QUIZ → CONCEPT PROFILE → KNOWLEDGE GRAPH → MATCH → HUMAN APPROVAL → SESSION
     → FOLLOW-UP EVALUATION → LEARNING GAIN → UPDATED PROFILE → UPDATED GRAPH → NEW MATCH
```

Everything runs **without an API key** (`DEMO_MODE=true`), so the full lifecycle is
demonstrable offline. Set `DEMO_MODE=false` with an `OPENROUTER_API_KEY` to use real models.

---

## 1. Quick start

```bash
cd conceptbridge
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # works as-is, no key needed

python scripts/run_demo.py         # full lifecycle in one command
python -m pytest                   # 25 tests, no network required
uvicorn demo.conceptbridge.api.main:app --reload    # API at http://127.0.0.1:8000/docs
```

Frontend (optional, in a second terminal):

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173, proxies /api to port 8000
```

Seed the database for the UI:

```bash
python scripts/seed_demo.py        # prints a run_id
curl -X POST localhost:8000/api/v1/profiling/run -H 'content-type: application/json' -d '{"run_id":"RUN-XXXX"}'
curl -X POST localhost:8000/api/v1/matching/run  -H 'content-type: application/json' -d '{"run_id":"RUN-XXXX"}'
```

Reset everything with `python scripts/reset_demo.py`.

---

## 2. Project tree

```
conceptbridge/
├── slice/                        # generic agent engine (no domain knowledge)
│   ├── config.py                 # env/.env settings, DEMO_MODE fallback
│   ├── budget.py                 # infrastructure caps (calls, tokens)
│   └── llm.py                    # the ONLY OpenRouter caller + schema repair + fallback
├── demo/conceptbridge/           # the domain
│   ├── config.py                 # thresholds, weights, group sizes
│   ├── schema.py                 # typed contracts between steps
│   ├── state.py                  # persistent state machine
│   ├── orchestrator.py           # "what happens next" (infrastructure, not an agent)
│   ├── artifacts.py              # optional JSON snapshots
│   ├── profiling/                # Agent 1  (LLM: open-ended answers only)
│   ├── matchmaking/              # Agent 2  (graph + scoring, NO LLM)
│   ├── peer_learning/            # Agent 3  (LLM: session content)
│   ├── evaluation/               # Agent 4  (LLM: questions/prose, Python: all numbers)
│   ├── persistence/              # SQLAlchemy models + engine
│   ├── api/                      # FastAPI app and routes
│   └── seed/demo_data.py         # 8 students engineered into an interesting graph
├── scripts/                      # run_demo, seed_demo, reset_demo, run_backend
├── tests/                        # 25 tests, all offline
├── frontend/                     # React + Vite + Tailwind v4 dashboard
└── runtime/                      # SQLite db + JSON artifacts (gitignored)
```

`slice/` never imports domain code. Domain code never builds an HTTP request.

---

## 3. The four agents

| Agent | Question it answers | LLM? |
|---|---|---|
| Concept Profiling | What does the student know? | Only for open-ended answers (0–5, normalised to 0–1). MCQs are scored in Python. |
| Matchmaking | Who can teach whom, about what? | **Never.** Fully deterministic and explainable. |
| Peer Learning | How should they teach and learn? | Yes — explanations, examples, activities, understanding checks. |
| Evaluation | Did learning occur? | Yes for question generation and prose grading. **No** for gain or effectiveness. |

The orchestrator and the graph are infrastructure, not agents.

### LLM call map

| Step name | Where | Stub in DEMO_MODE |
|---|---|---|
| `profiling:open_ended` | `profiling/agent.py` | keyword-coverage grader |
| `peer_learning:session` | `peer_learning/agent.py` | one round per relationship |
| `evaluation:questions` | `evaluation/agent.py` | 2 MCQ + 1 open per concept |
| `evaluation:open_ended` | `evaluation/agent.py` | same keyword grader |

Anything not in this table is Python.

---

## 4. State machine

```
INPUT → PROFILING → MATCHING → WAITING_FOR_APPROVAL → SESSION → EVALUATION → UPDATED_PROFILE → FINISHED

MATCHING              ── no eligible group ──→ NO_MATCH_FOUND → FINISHED
WAITING_FOR_APPROVAL  ── rejected ──→ MATCHING
EVALUATION            ── ineffective (gain < threshold) ──→ MATCHING
```

Transitions are validated against an allow-list (`state.ALLOWED`); an illegal transition
raises `InvalidTransition`. Every transition is written to `state_transitions`, so a run
can be inspected, replayed and resumed after a restart
(`GET /api/v1/runs/{run_id}/resume`). No LLM ever picks a state.

---

## 5. Graph construction algorithm

For every ordered pair of distinct students **A, B** and every concept **c**:

```
teacher_score = score(A, c)
learner_score = score(B, c)
transfer_gap  = teacher_score − learner_score

create edge A → B for c  if
    teacher_score >= STRENGTH_THRESHOLD   (0.70)
and learner_score <  GAP_THRESHOLD        (0.60)
and transfer_gap  >= MIN_TRANSFER_GAP     (0.20)
```

`edge_score` is the mean transfer gap of the concepts on that edge. Derived features:
reciprocal pairs, directed cycles (length 3…`MAX_GROUP_SIZE`, bounded search), knowledge
hubs (out-degree ≥ `HUB_OUT_DEGREE`), concept bottlenecks (learners/teachers ≥
`BOTTLENECK_RATIO`), isolated students (no in- or out-edges), and graph health metrics.

### Dynamic update

After an **effective** session the learner's `concept_scores` row is raised to the
post-session score and the current graph is rebuilt from the new profiles: edges whose
gap closed disappear, newly eligible edges appear. History is never deleted —
`edge_stats`, `learning_gains`, `profile_updates`, `match_candidates` and
`state_transitions` all survive the rebuild and feed back into future scoring.

### Group scoring

```
score =  0.30·coverage + 0.15·reciprocity + 0.25·transfer_strength
       + 0.10·fairness + 0.20·observed_effectiveness
       − 0.25·previous_match_penalty − 0.20·teaching_load_penalty
```

Every component is returned with the proposal, which is what powers the "Why this group?"
panel. Weights and thresholds live in `demo/conceptbridge/config.py` / `.env`.

---

## 6. Database schema (SQLite)

`students`, `concepts`, `questions`, `student_answers`, `concept_scores` (current),
`profile_updates` (history), `knowledge_edges` + `edge_concepts` (current graph),
`edge_stats` (observed effectiveness per teacher/learner/concept), `match_candidates`,
`sessions`, `session_rounds`, `evaluations`, `learning_gains`, `state_runs`,
`state_transitions`.

SQLite is the source of truth; `runtime/artifacts/<run_id>/*.json` holds optional
snapshots (profile, graph before/after, match, session plan, learning gains).

---

## 7. API

Base path `/api/v1`, interactive docs at `/docs`.

| Area | Endpoints |
|---|---|
| health | `GET /health` |
| students | `POST/GET /students`, `GET /students/{id}`, `GET /students/{id}/profile`, `GET /profiles` |
| concepts / questions | `POST/GET /concepts`, `POST/GET /questions` |
| quiz & profiling | `POST /quiz/submit`, `POST /profiling/run` |
| graph | `GET /graph`, `/graph/edges`, `/graph/students/{id}`, `/graph/cycles`, `/graph/reciprocal`, `/graph/hubs`, `/graph/bottlenecks`, `/graph/isolated`, `/graph/health`, `POST /graph/rebuild` |
| matching | `POST /matching/run`, `GET /matching/current`, `GET /matching/history`, `POST /matching/{id}/approve`, `POST /matching/{id}/reject` |
| sessions | `POST /sessions/generate`, `GET /sessions/{id}`, `POST /sessions/{id}/start`, `POST /sessions/{id}/complete` |
| evaluation | `POST /evaluations/{session_id}/generate`, `GET /evaluations/{id}`, `POST /evaluations/{id}/submit` |
| runs & analytics | `POST /runs`, `GET /runs/{id}`, `GET /runs/{id}/history`, `POST /runs/{id}/resume`, `GET /analytics/overview` |

Example:

```bash
curl -X POST localhost:8000/api/v1/quiz/submit -H 'content-type: application/json' \
  -d '{"answers":[{"student_id":"S001","question_id":"Q-C_REC-1","answer":"A"}]}'

curl localhost:8000/api/v1/graph/health
curl -X POST localhost:8000/api/v1/matching/MATCH-XXXX/approve \
  -H 'content-type: application/json' -d '{"decided_by":"instructor"}'
```

Evaluation answer keys are stripped from every API response; clients cannot write
learning gains or graph edges directly — both are derived server-side.

---

## 8. What the demo shows

`python scripts/run_demo.py` seeds 8 students across 8 concepts and prints:

1. concept vectors (MCQ deterministic + open-ended via the LLM path),
2. graph health, the reciprocal pair, a 3-person cycle, hubs, the SQL-Joins bottleneck and the isolated student (S008),
3. a proposed group with its full score breakdown,
4. approval → generated session → completion,
5. a follow-up evaluation with per-concept pre/post scores and gains,
6. the rebuilt graph after learning,
7. an **ineffective** session that routes `EVALUATION → MATCHING` instead of updating profiles,
8. a `NO_MATCH_FOUND → FINISHED` run for the isolated student.

---

## 9. Tests

```bash
python -m pytest
```

Covers MCQ scoring, open-ended stub grading, concept aggregation, profile creation, edge
creation and rejection, reciprocal/cycle/hub/bottleneck/isolated detection, group scoring
and size bounds, learning gain, the effective/ineffective decision, profile update,
dynamic edge update, historical preservation, every state transition including the
illegal-transition guard, resume-after-restart, the no-match path, and the whole
lifecycle over HTTP. No test needs an OpenRouter key.

---

## 10. Known limitations

- Scores are per-concept means; there is no item-response or confidence model.
- Cycle enumeration is exponential in principle and is bounded by `MAX_GROUP_SIZE` and a
  200-cycle cap; for a large cohort, swap in `networkx.simple_cycles`.
- Profile updates take the post-session score at face value (one evaluation, no decay,
  no retention check later).
- Sessions are structured artifacts, not live chat/video.
- Group formation is greedy (best-scoring candidate), not a global assignment optimiser;
  repeated runs rely on the fairness and previous-match penalties rather than a solver.
- `run_profiling` re-scores answers belonging to the given run only, so re-running it on
  an old run will overwrite those students' post-session scores.
- Auth, multi-tenant separation and rate limiting are out of scope.
