# ConceptBridge — agentic peer-match pilot

A CLI agent that turns one quiz into **reciprocal** peer-learning pairs,
asks a human to approve each pairing, runs a peer session, measures the
learning gain, and **goes back and re-matches** when the session did not
work.

Deterministic Python owns every number and every transition. The language
model only explains a match and writes the session plan.

```
INPUT → PROFILING → MATCHING → WAITING_FOR_APPROVAL
                       ↑                │
                       │ reject/ineffective
                       │                ▼
                       │   SESSION → EVALUATION → UPDATED_PROFILE → FINISHED
                       └────────────────┘
MATCHING → NO_SUITABLE_MATCH
```

---

## 1. Install

Python 3.10+ is all you need.

```bash
cd conceptbridge
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # optional, see below
```

**`requirements.txt` is optional.** The project ships a Pydantic
compatibility layer (`slice/compat.py`): if `pydantic` is installed it is
used, otherwise a strict built-in fallback takes over. The same is true
of `pytest` — `python tests/run_tests.py` runs the suite with no packages
at all. There are **no other dependencies**; the OpenRouter client is
built on the standard library.

## 2. Environment

```bash
cp .env.example .env
```

```env
OPENROUTER_API_KEY=sk-or-...
SLICE_MODEL=openai/gpt-4o-mini
SLICE_FALLBACK_MODEL=meta-llama/llama-3.1-8b-instruct
SLICE_ESCALATION_MODEL=anthropic/claude-3.5-sonnet
```

The key is read only by `slice/config.py`, is never hard-coded and is
never printed. `.env` is git-ignored.

## 3. Run it

```bash
# offline, no API key, no cost — the demo path
python scripts/conceptbridge.py run --stub

# the three scenarios
python scripts/conceptbridge.py run --stub --scenario success
python scripts/conceptbridge.py run --stub --scenario reject
python scripts/conceptbridge.py run --stub --scenario ineffective
python scripts/conceptbridge.py run --stub --scenario no-match

# non-interactive approval (used by tests and CI)
python scripts/conceptbridge.py run --stub --approval yes
python scripts/conceptbridge.py run --stub --approval no
python scripts/conceptbridge.py run --stub --approval no,yes

# live OpenRouter (needs OPENROUTER_API_KEY; ~2 model calls)
python scripts/conceptbridge.py run

# pause, then continue in a new process
python scripts/conceptbridge.py run --stub --stop-after MATCHING
python scripts/conceptbridge.py resume --stub --approval yes

# look at what actually happened, then clear it
python scripts/conceptbridge.py inspect
python scripts/conceptbridge.py reset
```

With no `--approval` flag the run is **interactive**: it stops and waits
for `y`/`n` at `WAITING_FOR_APPROVAL`. It never approves by itself.

## 4. Test

```bash
pytest -q                     # if pytest is installed
python tests/run_tests.py     # otherwise; no dependencies
```

55 tests: profiling, matching, evaluation, the state machine, persistence,
failure handling and prompt injection.

## 5. What to look at during a demo

The terminal is the story; `records.jsonl` is the proof.

```bash
python scripts/conceptbridge.py run --stub --scenario ineffective
python scripts/conceptbridge.py inspect
```

```
MATCHING              match_candidate    S1|S2 score=0.83
WAITING_FOR_APPROVAL  approval           S1|S2 approved=True
EVALUATION            outcome            S1|S2 effective=False
EVALUATION            state_transition   EVALUATION -> MATCHING     ← the agentic bit
MATCHING              match_candidate    S1|S3 score=0.73
EVALUATION            outcome            S1|S3 effective=True
UPDATED_PROFILE       profile_update     S1 SQL Joins 0.35 -> 0.78
```

## 6. Layout

```
slice/                    reusable engine — knows nothing about ConceptBridge
  config.py               environment + .env parsing (the only place)
  compat.py               pydantic-or-fallback models
  errors.py               infrastructure error types
  budget.py               token/attempt budgets (never domain counters)
  records.py              append-only record model
  store.py                state.json + records.jsonl
  llm.py                  OpenRouter gateway, model chain, fallbacks
  structured.py           JSON extraction, validation, schema repair
  runner.py               explicit state-machine execution

demo/conceptbridge/       the agent — depends on slice, never the reverse
  SPEC.md                 the specification this was built from
  schema.py               typed domain models
  profiling.py            quiz → concept profiles      (deterministic)
  matching.py             reciprocal compatibility      (deterministic)
  evaluation.py           learning gain, profile deltas (deterministic)
  session.py              match explanation + session plan  (LLM + fallback)
  flow.py                 state handlers and transitions
  main.py                 run / resume / inspect / reset
  stub.py                 offline deterministic provider
  prompts/                versioned prompts with injection defences
  data/                   the pilot dataset

scripts/conceptbridge.py  CLI
tests/                    7 test modules + a no-dependency runner
runtime/conceptbridge/    state.json, records.jsonl (git-ignored)
```

## 7. Adding a frontend or backend later

Nothing here has to be thrown away.

| You want | Touch |
|---|---|
| HTTP API | new `api/` package calling `demo.conceptbridge.main.run/resume` |
| web approval instead of CLI | `flow._read_approval` — swap the input source |
| real database | `slice/store.py` only; the interface is `append / read_records / save_state / load_state` |
| different model | `.env` (`SLICE_MODEL`), nothing in the code |
| more concepts or students | `data/*.csv` — no code change |
| different thresholds | `matching.STRENGTH_THRESHOLD`, `GAP_THRESHOLD`, `evaluation.LEARNING_GAIN_THRESHOLD` |
| more re-match attempts | `flow.MAX_REMATCH_ATTEMPTS` |

## 8. Checklist

- [x] `python scripts/conceptbridge.py run --stub` works with no API key
- [x] concept profiles derived from question-level evidence, not stored
- [x] reciprocal compatibility is deterministic and documented
- [x] candidate match is explainable (LLM, with deterministic fallback)
- [x] CLI accepts human approval and never auto-approves
- [x] rejection causes a backward transition and excludes the pair
- [x] approved match generates a peer-learning session
- [x] follow-up quiz evaluated; gain computed in Python
- [x] effective outcome updates the profile; ineffective re-matches
- [x] previously rejected/ineffective pairs are excluded
- [x] no suitable match terminates cleanly
- [x] state persists to JSON/JSONL and the run resumes
- [x] OpenRouter integration via `slice.llm.complete` only
- [x] invalid model output repaired, then failed safely
- [x] adversarial student text cannot change scores or rules
- [x] bounded: token/attempt budget, re-match limit, max-steps guard
- [x] full test suite passes
- [x] no frontend, no backend routes
