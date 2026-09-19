# ConceptBridge Progress Report

## Completed

The core agentic pipeline is implemented and working locally.

### Agent Workflow

```text
INPUT
→ PROFILING
→ MATCHING
→ WAITING_FOR_APPROVAL
→ SESSION
→ EVALUATION
→ UPDATED_PROFILE
→ FINISHED
```

Supported alternative flows:

```text
Rejected Match
→ MATCHING

Ineffective Session
→ MATCHING
→ Next Candidate

No Valid Candidates
→ NO_SUITABLE_MATCH
```

---

## Implemented Components

### Profiling & Matching
- Pydantic schemas for profiles, matches, approvals, sessions, outcomes, updates, and failures
- Deterministic quiz profiling from question-level CSV evidence
- Reciprocal matching based on strengths and learning gaps
- Deterministic compatibility scoring
- LLM/stub-generated match explanations

### Session Management
- Human approval through CLI
- Generated peer-learning session plans
- Teaching prompts and concept guidance
- Interactive follow-up score collection

### Evaluation & Updates
- Deterministic learning-gain calculation
- Profile updates after effective sessions
- Rejection and ineffective-match exclusion
- Rematching with bounded attempts

### Persistence
- JSON state persistence
- Append-only JSONL event history
- Resume and inspect commands

### Configuration
- Stub mode without API keys
- OpenRouter integration through `slice.llm.complete`
- Configurable quiz, mapping, and follow-up CSV paths

---

## Interactive CLI

Run:

```powershell
.\.venv\Scripts\python.exe scripts\conceptbridge.py run --stub
```

The CLI displays:

1. Recommended match
2. Compatibility score
3. Teaching concepts
4. Match rationale
5. Approval prompt
6. Generated session plan
7. Teaching prompts
8. Follow-up questions
9. Post-session score inputs
10. Learning gains
11. Effective/ineffective result
12. Updated profiles

---

## Input Data

The default pilot dataset contains:

- 6 students
- 12 quiz questions
- 6 concepts
- Question-to-concept mappings
- Follow-up quiz results

Custom files can be supplied:

```powershell
.\.venv\Scripts\python.exe scripts\conceptbridge.py run --stub `
  --quiz path\to\quiz.csv `
  --question-concepts path\to\question_concepts.csv `
  --followup-quiz path\to\followup_quiz.csv
```

---

## Follow-Up Quiz Status

The system currently supports two evaluation paths.

### Interactive Path

```text
Generated Session
→ Human-entered Follow-up Scores
→ Deterministic Evaluation
```

The user manually enters post-session scores which are evaluated by the system.

### Fixture Path

```text
Generated Session
→ Fixture-Based Automated Evaluation
```

The sample `followup_quiz.csv` provides reproducible success and ineffective outcomes for testing.

---

## Testing

Current test suite status:

```text
85 passed
```

Coverage includes:

- Schema validation
- Profiling
- Reciprocal matching
- Non-reciprocal rejection
- Approval and rejection
- Effective learning outcomes
- Ineffective learning outcomes
- Rematching logic
- Persistence
- Profile updates
- Adversarial student input
- Interactive follow-up handling
- CLI compatibility

Compilation verification:

```powershell
.\.venv\Scripts\python.exe -m compileall -q demo scripts
```

---

## Persistence

Runtime data is stored in:

```text
runtime/conceptbridge/state.json
runtime/conceptbridge/records.jsonl
```

Stored state includes:

- Current state
- Original profiles
- Updated profiles
- Candidate history
- Approval history
- Sessions
- Outcomes
- Profile updates
- Excluded matches
- Rematch count

---

## Available Commands

```powershell
.\.venv\Scripts\python.exe scripts\conceptbridge.py reset

.\.venv\Scripts\python.exe scripts\conceptbridge.py run --stub

.\.venv\Scripts\python.exe scripts\conceptbridge.py run --stub --approval yes

.\.venv\Scripts\python.exe scripts\conceptbridge.py run --stub --scenario ineffective

.\.venv\Scripts\python.exe scripts\conceptbridge.py run --stub --scenario no-match

.\.venv\Scripts\python.exe scripts\conceptbridge.py resume

.\.venv\Scripts\python.exe scripts\conceptbridge.py inspect

.\.venv\Scripts\python.exe -m pytest -q
```

---

## Current Limitations

The project is currently a pilot CLI application and not yet a production system.

Limitations include:

- No browser frontend
- No REST API
- Follow-up quiz questions are generated in the session plan but are not stored as structured question objects
- Interactive evaluation currently accepts final scores rather than individual question responses
- Sample demonstration data is still bundled with the project
- Live OpenRouter mode has not yet been fully demonstrated using a production API key
- No database server
- No authentication system
- No deployment pipeline



---

## Overall Status

The project has successfully reached a **working deterministic agentic pilot** stage.

```text
Quiz Evidence
→ Learner Profiles
→ Reciprocal Match
→ Human Approval
→ Generated Peer Session
→ Follow-up Evaluation
→ Profile Update
→ Persistent Outcome
```


**Project Status:** Functional Agentic Prototype  
**Stage:** End-to-End Workflow Complete  
**Testing Status:** 85 Tests Passing  
**Persistence:** Implemented  
**CLI Demonstration:** Complete  
**Next Focus:** Frontend or Enhanced Assessment Engine