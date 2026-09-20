# Design Rationale

## Project

ConceptBridge – Agentic Peer Learning Matchmaking System

---

## Problem Statement

Students within a classroom often possess complementary strengths and weaknesses across different concepts.

Faculty members rarely have the time or visibility needed to manually identify effective peer-learning opportunities across an entire cohort.

As a result, valuable knowledge-transfer opportunities remain undiscovered.

---

## Why ConceptBridge?

ConceptBridge transforms assessment results into actionable peer-learning recommendations.

Instead of relying solely on overall marks, the system analyzes concept-level competencies and identifies opportunities for meaningful knowledge transfer between students.

---

## Key Design Decisions

### Concept-Level Profiling

Student performance is represented at the concept level.

This enables the system to identify:

- Strength areas
- Learning gaps
- Potential teaching opportunities

rather than relying on a single aggregate score.

---

### Reciprocal Matchmaking

Matches are generated based on mutual benefit.

Each recommendation considers:

- What one student can teach.
- What another student can learn.
- Compatibility between concept strengths and weaknesses.

This encourages collaborative peer learning rather than one-way tutoring.

---

### Knowledge Transfer Graph (KTG)

A major architectural enhancement was the introduction of the Knowledge Transfer Graph.

The KTG represents:

- Students as nodes.
- Knowledge-transfer opportunities as directed weighted edges.
- Concept-specific learning relationships.

Benefits include:

- Visualization of classroom knowledge flow.
- Identification of knowledge hubs.
- Discovery of isolated learners.
- Better handling of odd-sized cohorts.
- Foundation for future group-learning recommendations.

---

### Agentic Architecture

ConceptBridge combines deterministic educational logic with AI-assisted reasoning.

The agent:

- Profiles student competencies.
- Generates peer-learning recommendations.
- Explains recommendations.
- Supports learning-session planning.

The architecture supports both:

#### Online Mode

OpenRouter-enabled execution with LLM-assisted reasoning and explanation generation.

#### Offline Mode

Graph-based and rule-based execution when external AI services are unavailable.

This ensures reliability during demonstrations and real-world deployment.

---

### Human-in-the-Loop

Faculty mentors remain part of the decision-making process.

Recommendations can be reviewed before learning sessions are finalized, ensuring educational oversight.

---

### Learning Gain Evaluation

After each learning session:

- Student understanding is reassessed.
- Learning gains are measured.
- Profiles are updated.

This allows the system to continuously improve future recommendations.

---

## Limitations

- Current evaluation uses a limited demonstration dataset.
- Match quality depends on assessment quality.
- Frontend visualization is still under active development.
- Group-learning recommendations are planned but not yet implemented.

---

## Future Work

- Multi-pair classroom matchmaking.
- Group-learning recommendations.
- Automated assessment ingestion.
- Advanced graph analytics.
- Faculty dashboards.
- Longitudinal learning analytics.

---

## Conclusion

ConceptBridge combines concept-level profiling, reciprocal matchmaking, Knowledge Transfer Graph analysis, human oversight, and optional LLM-assisted reasoning to create a scalable and explainable peer-learning ecosystem.