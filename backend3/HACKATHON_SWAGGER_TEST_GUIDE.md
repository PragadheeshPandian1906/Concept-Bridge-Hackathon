# ConceptBridge — Swagger UI hackathon demo guide

This guide demonstrates the complete adaptive, human-in-the-loop state machine using Swagger UI. It assumes the API is running at `http://127.0.0.1:8000/docs`.

> Keep Swagger open in one browser tab. Use a terminal only for setup/reset commands. All API interactions in this guide are performed in Swagger.

## 1. Setup

Create a local `.env` from `.env.example`. To show the LLM-driven session and evaluation content, set your own key locally:

```dotenv
CONCEPTBRIDGE_DEMO_MODE=false
OPENROUTER_API_KEY=your_openrouter_key
CONCEPTBRIDGE_LLM_MODEL=openai/gpt-4.1-mini
CONCEPTBRIDGE_LLM_FALLBACK_MODEL=openai/gpt-4.1-mini
```

Start from clean demo data and launch the API:

```powershell
python scripts/seed_demo.py
uvicorn demo.conceptbridge.api:app --reload
```

Open `http://127.0.0.1:8000/docs` and use **Try it out** then **Execute** for each request below.

## 2. Quick API health check

1. Execute `GET /health`.
2. Execute `GET /api/v1/students`; it should show eight students (`S001` through `S008`).
3. Execute `GET /api/v1/concepts`; it should show the eight seeded concepts.
4. Execute `GET /api/v1/graph`.

Use the graph response to point out active directed transfer edges, reciprocal opportunities, knowledge hubs, isolated students, and bottlenecks.

## 3. Main demo — human rejection → rematching

### Step 3.1: Discover every valid candidate

Execute:

```http
POST /api/v1/matching/run
```

There is no request body.

Record the response values:

- `id` — the run ID, called `RUN_A` below.
- `current_state` — must be `WAITING_FOR_HUMAN_REVIEW`.
- `candidate_count` — all currently valid candidates.
- `generation.combinations_considered` — for eight students, defaults are `2: 28`, `3: 56`, `4: 70`, `5: 56`.

Open any candidate in the response and show its `relationships`, `evidence.reasons`, `knowledge_coverage`, `fairness`, `reciprocity`, and `knowledge_cycle` values. Explain that a candidate is valid because it contains meaningful transfer edges; cycles and reciprocal edges improve ranking but are **not required**.

### Step 3.2: Reject a candidate

Choose one `id` from the returned `candidates` array (`CAN_REJECT`). Execute:

```http
POST /api/v1/matching/{candidate_id}/reject
```

Path parameter:

```text
candidate_id = CAN_REJECT
```

Body:

```json
{
  "actor": "judge-demo-facilitator",
  "reason": "Please propose a different knowledge-transfer group."
}
```

Expected result:

- New `id` / run ID (`RUN_B`).
- `iteration: 2`.
- `current_state: WAITING_FOR_HUMAN_REVIEW`.
- A fresh candidate pool.

This is the first core story: **the system recommends, the human rejects, and the system rematches instead of stopping.**

## 4. Single-candidate approval → LLM peer session → ineffective rematch

### Step 4.1: Approve a non-top candidate

From `RUN_B.candidates`, deliberately select the second or third candidate rather than the first (`CAN_APPROVE`). Execute:

```http
POST /api/v1/matching/{candidate_id}/approve
```

Path parameter:

```text
candidate_id = CAN_APPROVE
```

Body:

```json
{
  "actor": "judge-demo-facilitator",
  "duration_minutes": 45
}
```

Expected result:

- `run.current_state: SESSION`.
- A `session.id` (`SES_A`).
- A session `plan` with teaching rounds.
- With OpenRouter enabled, `plan.source: openrouter`.

Show that every plan round uses the fixed teacher, learner, and concept from the deterministic candidate relationships. The LLM generates *how* to teach, not *who teaches whom*.

### Step 4.2: Complete the session and create a follow-up evaluation

Execute:

```http
POST /api/v1/sessions/{session_id}/complete
```

Path parameter:

```text
session_id = SES_A
```

There is no request body.

Expected result:

- `status: PENDING`.
- An evaluation `id` (`EVAL_A`).
- Follow-up `questions` that target only concepts taught in the approved session.
- With OpenRouter enabled, `source: openrouter`.

### Step 4.3: Submit deliberately ineffective results

Execute:

```http
POST /api/v1/evaluations/{evaluation_id}/submit
```

Path parameter:

```text
evaluation_id = EVAL_A
```

Build `post_scores` from the concept IDs in `EVAL_A.questions`. Use `0.0` for every concept to guarantee an ineffective result. Example (replace these keys with the concepts returned by your evaluation):

```json
{
  "post_scores": {
    "recursion": 0.0,
    "trees": 0.0,
    "sql_joins": 0.0
  }
}
```

Expected result:

- `result.effective: false`.
- Each gain is below the configured `0.20` threshold.
- `rematch.current_state: WAITING_FOR_HUMAN_REVIEW`.
- A new candidate pool is returned.

This is the second core story: **the session did not work, so ConceptBridge records the outcome and discovers alternatives.**

## 5. Effective learning → profile update → graph update → finished

### Step 5.1: Approve a candidate from the ineffective-rematch response

Use any pending candidate ID from `rematch.candidates` in:

```http
POST /api/v1/matching/{candidate_id}/approve
```

Body:

```json
{
  "actor": "judge-demo-facilitator",
  "duration_minutes": 45
}
```

Save the returned session ID as `SES_B`.

### Step 5.2: Complete `SES_B`

Execute:

```http
POST /api/v1/sessions/{session_id}/complete
```

Set `session_id = SES_B`; save the returned evaluation ID as `EVAL_B`.

### Step 5.3: Submit effective results

Execute:

```http
POST /api/v1/evaluations/{evaluation_id}/submit
```

Use all distinct concept IDs returned in `EVAL_B.questions`, with `1.0` scores. Example:

```json
{
  "post_scores": {
    "recursion": 1.0,
    "normalization": 1.0,
    "trees": 1.0
  }
}
```

Expected result:

- `result.effective: true`.
- `run.current_state: FINISHED`.
- Learner concept profiles are updated.
- The current graph is rebuilt while historical results remain stored.

Execute `GET /api/v1/graph` again. Explain that transfer edges can disappear when a learner’s updated score reduces a former transfer gap below the configured threshold.

## 6. Batch workflow — approve all → complete all → submit all

Reset before this independent batch demo:

```powershell
python scripts/seed_demo.py
```

### Step 6.1: Start a new matching run

Execute `POST /api/v1/matching/run` and save its `id` as `RUN_BATCH`.

### Step 6.2: Human batch approval

Execute:

```http
POST /api/v1/matching/runs/{run_id}/approve-all
```

Path parameter:

```text
run_id = RUN_BATCH
```

Body:

```json
{
  "actor": "judge-demo-facilitator",
  "duration_minutes": 45
}
```

Expected result: every pending candidate is explicitly human-approved and receives one `PLANNED` session.

### Step 6.3: Complete the complete batch

Execute:

```http
POST /api/v1/matching/runs/{run_id}/sessions/complete-all
```

Set `run_id = RUN_BATCH`. There is no request body.

Expected result: `run.current_state: EVALUATION` and an `evaluations` list.

### Step 6.4: Submit every evaluation in the batch

Execute:

```http
POST /api/v1/matching/runs/{run_id}/evaluations/submit-all
```

Set `run_id = RUN_BATCH`. The request must contain **every** pending evaluation ID returned in Step 6.3.

Structure:

```json
{
  "evaluations": [
    {
      "evaluation_id": "EVAL-FIRST-ID",
      "post_scores": {
        "recursion": 1.0,
        "trees": 1.0
      }
    },
    {
      "evaluation_id": "EVAL-SECOND-ID",
      "post_scores": {
        "arrays": 1.0,
        "sql_joins": 1.0
      }
    }
  ]
}
```

For each evaluation, use each distinct `concept_id` listed in that evaluation’s `questions` array once. Do not omit any pending evaluation ID.

Batch result rules:

- Every evaluation effective → `run.current_state: FINISHED`.
- At least one evaluation ineffective → a global all-student rematch appears in `rematch`, with `WAITING_FOR_HUMAN_REVIEW`.

## 7. MCQ versus open-ended profiling demonstration

Run this as a separate short demonstration. Reset afterwards if you want to repeat the matching demo.

### MCQ: no LLM call

1. Execute `POST /api/v1/questions`:

```json
{
  "id": "Q-DEMO-MCQ",
  "concept_id": "recursion",
  "type": "mcq",
  "text": "What is the base case of a recursive function?",
  "correct_answer": "A condition that stops recursive calls",
  "max_marks": 1,
  "rubric": ""
}
```

2. Execute `POST /api/v1/questions/Q-DEMO-MCQ/answers`:

```json
{
  "student_id": "S001",
  "answer": "A condition that stops recursive calls"
}
```

The returned normalized score is deterministic (`1.0`) and does not use an LLM.

### Open answer: OpenRouter call

1. Execute `POST /api/v1/questions`:

```json
{
  "id": "Q-DEMO-OPEN",
  "concept_id": "recursion",
  "type": "open",
  "text": "Explain how recursion terminates and give a simple example.",
  "correct_answer": null,
  "max_marks": 5,
  "rubric": "Explain a base case, recursive case, and why the base case prevents infinite recursion."
}
```

2. Execute `POST /api/v1/questions/Q-DEMO-OPEN/answers`:

```json
{
  "student_id": "S001",
  "answer": "A recursive function calls itself with a smaller input. It stops at a base case, such as factorial(0) returning 1. Without the base case, calls would continue forever."
}
```

With OpenRouter configured, the answer is assessed using structured LLM output. Execute `POST /api/v1/profiling/run` afterward to aggregate submitted answers into concept scores.

## 8. No-match branch (separate clean database)

This demonstrates `MATCHING → NO_MATCH_FOUND`. Do this only after the main demo, because it uses a clean database.

1. Stop the server.
2. In `.env`, temporarily change:

```dotenv
CONCEPTBRIDGE_DATABASE_PATH=runtime/no_match_demo.db
```

3. Restart Uvicorn and open Swagger.
4. Create one concept with `POST /api/v1/concepts`:

```json
{
  "id": "demo_concept",
  "name": "Demo Concept",
  "description": "No-match test concept"
}
```

5. Create two students using `POST /api/v1/students`:

```json
{
  "id": "N001",
  "name": "No Match One",
  "email": "n001@example.test",
  "metadata": {}
}
```

Create `N002` with a different name/email.

6. For each student, execute `PUT /api/v1/students/{student_id}/scores` using:

```json
{
  "concept_id": "demo_concept",
  "score": 0.5,
  "source": "demo"
}
```

Both scores are below the teaching-strength threshold, so no transfer edge can exist.

7. Execute `POST /api/v1/matching/run`.

Expected result:

```text
current_state: NO_MATCH_FOUND
candidate_count: 0
```

Restore `CONCEPTBRIDGE_DATABASE_PATH=runtime/conceptbridge.db`, rerun `python scripts/seed_demo.py`, and restart the API to return to the main demo data.

## 9. Final evidence for judges

Use `GET /api/v1/analytics` and `GET /api/v1/runs/{run_id}` to show persisted evidence:

- State transition history.
- Human approval/rejection decisions.
- Candidate pools and deterministic evidence.
- Effective/ineffective historical outcomes.
- New rematch iterations.
- Updated graph analytics.

## 10. Recommended live presentation story

1. “Students completed a concept-level assessment.”
2. “ConceptBridge builds a deterministic knowledge-transfer graph.”
3. “It considers every group size from two through five, not merely cycles or reciprocal pairs.”
4. “The human rejects a recommendation; the system rematches.”
5. “The human approves a different candidate; the LLM creates the teaching plan.”
6. “The LLM creates a targeted follow-up quiz, but Python calculates learning gain.”
7. “An ineffective outcome triggers adaptive global rematching.”
8. “An effective outcome updates profiles and the graph, preserving all history.”
