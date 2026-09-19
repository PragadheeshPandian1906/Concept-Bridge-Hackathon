# ConceptBridge

ConceptBridge demonstrates reciprocal peer learning from one question-level quiz. Python deterministically derives profiles, reciprocal compatibility, learning gains, thresholds, and state transitions. The model only explains a chosen match and drafts a session plan.

States are `INPUT -> PROFILING -> MATCHING -> WAITING_FOR_APPROVAL -> SESSION -> EVALUATION -> UPDATED_PROFILE -> FINISHED`. Rejection or ineffective learning returns to `MATCHING`; no eligible candidate reaches `NO_SUITABLE_MATCH`; failures reach `FAILED`.

State is JSON in `runtime/conceptbridge/state.json`; append-only audit records are JSONL beside it. The CLI supports stub mode, live OpenRouter mode through `slice.llm.complete`, resume, inspect, reset, approval, and reproducible success/ineffective/no-match scenarios. Frontend, API, authentication, database server, taxonomy generation, graph, RL, and multi-agent orchestration are intentionally absent.