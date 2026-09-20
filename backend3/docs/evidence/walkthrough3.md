# Walkthrough 3

## Date
20 September 2026

## Tester
Pre Final Year Computer Science Student

## Objective

Evaluate whether users can clearly understand the agentic architecture of ConceptBridge and identify where LLM-assisted reasoning is involved in the workflow.

## Task Given

1. Review the complete ConceptBridge workflow.
2. Generate student competency profiles.
3. Generate peer-learning recommendations.
4. Review the Knowledge Transfer Graph.
5. Observe both online and offline execution modes.
6. Identify where AI-assisted reasoning occurs within the system.

## Observations

- The tester understood the profiling workflow and peer-learning recommendations.
- The tester was able to understand the Knowledge Transfer Graph and how knowledge-transfer opportunities are represented.
- The tester could not immediately identify where the LLM was involved in the workflow.
- The tester initially assumed the entire system was operating through deterministic graph-based logic.
- The distinction between graph-based reasoning and LLM-assisted reasoning was not obvious from the interface.

## Feedback

> "The workflow makes sense, but I can't tell where the AI model is actually being used."

> "Is the recommendation coming from the graph logic or from the LLM?"

> "What changes when the system runs without internet access?"

## Analysis

The feedback highlighted an explainability gap in the system architecture.

Although ConceptBridge integrates LLM-assisted reasoning, users could not clearly distinguish between:

- Concept profiling logic
- Matchmaking logic
- Knowledge Transfer Graph generation
- LLM-assisted session planning and evaluation

As a result, users found it difficult to understand which parts of the workflow were powered by traditional algorithms and which parts relied on AI-assisted reasoning.

## Action Taken

The team created a dedicated demonstration showcasing both online and offline execution modes.

### Online Mode

- OpenRouter API available.
- LLM-assisted reasoning enabled.
- Student profiling completed successfully.
- Matchmaking completed successfully.
- Knowledge Transfer Graph generated successfully.
- Session planning completed successfully.
- Learning-gain evaluation completed successfully.
- Complete end-to-end workflow demonstrated.

### Offline Mode

- OpenRouter API unavailable or disabled.
- Student profiling remained functional.
- Matchmaking remained functional.
- Knowledge Transfer Graph generation remained functional.
- Session planning failed due to LLM dependency.
- Evaluation failed due to LLM dependency.

The demonstration explicitly highlights:

- Where the OpenRouter client is invoked.
- Which workflow states depend on LLM support.
- Which workflow states continue to operate without external AI services.
- The current limitations of offline execution.

The team also documented offline limitations and identified offline session planning and evaluation as future enhancements.

## Result

Users can now clearly understand:

- Where the LLM is invoked within the workflow.
- Which components are powered by graph-based reasoning.
- Which components rely on LLM-assisted reasoning.
- Why offline execution currently supports profiling, matchmaking, and graph generation but not session planning and evaluation.

The demonstration significantly improved transparency and helped users understand the architecture and operational boundaries of the agent.

## Status

PASS – Feedback improved explainability of the agent architecture and helped identify documented limitations in offline execution.