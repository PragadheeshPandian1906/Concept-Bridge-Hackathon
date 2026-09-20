# ConceptBridge backend

A working FastAPI + SQLite backend for human-in-the-loop, adaptive peer learning. It deliberately separates a **candidate pool** from the single candidate a human approves.

## Critical matching guarantee

`POST /api/v1/matching/run` rebuilds the current transfer graph and enumerates every student combination whose size is in the configured inclusive range `MIN_GROUP_SIZE..MAX_GROUP_SIZE`. For each combination it gathers the internal directed transfer edges and returns it when it has at least one meaningful relationship and does not violate teaching-load limits.

Reciprocity and cycles are calculated as explainable ranking features only. Neither is a validity gate. Therefore a source fan-out such as `A -> B`, `A -> C`, `A -> D` is returned as a valid group, as are multiple-teacher, complementary, and mixed groups.

For eight students and the default maximum size of five the response reports these considered combinations:

| Size | Combinations |
| --- | ---: |
| 2 | 28 |
| 3 | 56 |
| 4 | 70 |
| 5 | 56 |

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/seed_demo.py
uvicorn demo.conceptbridge.api:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs). The database is at `runtime/conceptbridge.db` by default.

Run the automated demo discovery:

```powershell
python scripts/run_demo.py
```

To remove every record without reseeding demo data, run:

```powershell
python scripts/reset_empty_database.py
```

The schema remains intact, ready for manual student, concept, question, and answer creation through Swagger. The equivalent SQL is in `scripts/reset_empty_database.sql`.

Run the tests:

```powershell
python -m pytest -q
```

## Adaptive state flow

```text
INPUT -> PROFILING -> MATCHING -> WAITING_FOR_HUMAN_REVIEW
                                      | approve       | reject
                                      v               v
                                   SESSION          MATCHING (new iteration)
                                      |
                                  EVALUATION
                              effective | ineffective
                                        v       v
                           UPDATED_PROFILE     MATCHING (new iteration)
                                   |
                                FINISHED
```

Every transition is persisted in `runs` and `transitions`. Rejections are persisted as decisions and history records. A rematch excludes the rejected exact participant combination in the same root cycle when alternatives exist; it never treats that relationship as permanently invalid.

## Main endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/students` | Create a student |
| `PUT` | `/api/v1/students/{id}/scores` | Set a deterministic concept score |
| `POST` | `/api/v1/concepts` | Create a concept |
| `POST` | `/api/v1/questions` | Create a tagged question |
| `POST` | `/api/v1/questions/{id}/answers` | Submit and score an answer |
| `POST` | `/api/v1/profiling/run` | Aggregate quiz answers into profiles |
| `POST` | `/api/v1/graph/rebuild` | Recalculate active transfer edges |
| `GET` | `/api/v1/graph` | Inspect edges and graph health |
| `POST` | `/api/v1/matching/run` | Generate the full valid candidate pool |
| `GET` | `/api/v1/matching/{candidate_id}` | Inspect deterministic evidence |
| `POST` | `/api/v1/matching/{candidate_id}/approve` | Human selects any pending candidate |
| `POST` | `/api/v1/matching/runs/{run_id}/approve-all` | Human batch-approves all pending candidates and creates a session for each |
| `POST` | `/api/v1/matching/{candidate_id}/reject` | Persist a rejection and rematch |
| `POST` | `/api/v1/sessions/{session_id}/complete` | Create a targeted follow-up evaluation |
| `POST` | `/api/v1/matching/runs/{run_id}/sessions/complete-all` | Complete all planned batch sessions and return their evaluations |
| `POST` | `/api/v1/evaluations/{evaluation_id}/submit` | Server calculates gains and rematches if ineffective |
| `POST` | `/api/v1/matching/runs/{run_id}/evaluations/submit-all` | Submit every pending evaluation in a batch at once |
| `GET` | `/api/v1/runs/{run_id}` | Read persisted state history |
| `GET` | `/api/v1/analytics` | Read graph/runs/history analytics |

## Example human loop

```powershell
# after seeding and starting the API
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/matching/run

# approve/reject an ID returned in candidates; it is never auto-selected
Invoke-RestMethod -Method Post -ContentType application/json -Body '{"actor":"facilitator","reason":"Need wider coverage"}' http://127.0.0.1:8000/api/v1/matching/CAN-.../reject
```

Batch approval is explicitly human initiated:

```powershell
Invoke-RestMethod -Method Post -ContentType application/json -Body '{"actor":"facilitator","duration_minutes":45}' http://127.0.0.1:8000/api/v1/matching/runs/RUN-.../approve-all
```

It returns one planned session per candidate. Complete and submit each returned session separately; the run remains in `EVALUATION` until its batch is fully evaluated, then it either finishes or rematches.

## Layout

```text
slice/
   __init__.py      Reusable agent runtime exports
   llm.py           OpenRouter structured-output gateway and failure boundary
demo/conceptbridge/
  agents/          Profiling, peer-learning, and evaluation agents
  api.py           FastAPI endpoints
  config.py        All configurable thresholds and score weights
  db.py            SQLite schema and storage helpers
  graph.py         Deterministic current transfer graph and metrics
  matching.py      Exhaustive valid combination enumeration and scoring
  orchestrator.py  Persisted state machine plus approval/rematch loop
  seed.py          Eight-student demo data
scripts/           Seeding and discovery demo
tests/             Group enumeration, rejection, approval, evaluation tests
```

## LLM boundary and OpenRouter setup

`slice/` owns reusable agent mechanics; `demo/conceptbridge/` owns ConceptBridge decisions and schemas. MCQs, profiling aggregation, graph construction, candidate generation, group scoring, state transitions, and gains are deterministic. Open-ended profiling answers, learning-session plans, and follow-up evaluations call the reusable [`slice/llm.py`](slice/llm.py) gateway and validate structured OpenRouter responses, retrying with a configured fallback model.

To enable LLM features, add this to your uncommitted `.env` file and restart Uvicorn:

```dotenv
CONCEPTBRIDGE_DEMO_MODE=false
OPENROUTER_API_KEY=your_key_here
CONCEPTBRIDGE_LLM_MODEL=openai/gpt-4.1-mini
CONCEPTBRIDGE_LLM_FALLBACK_MODEL=openai/gpt-4.1-mini
```

LLM calls are limited to: grading open-ended profile answers, creating session language (objectives, examples, activities, and checks), and generating follow-up assessment questions. With `CONCEPTBRIDGE_STRICT_LLM=true`, OpenRouter/network/schema failures return HTTP `503`; no fallback plan, quiz, or grading result is created, and no approval/session transition is persisted. Set `CONCEPTBRIDGE_DEMO_MODE=true` only for intentional offline demonstrations. MCQs and matchmaking never call an LLM; the LLM cannot change participants, concepts, scores, or state transitions.
