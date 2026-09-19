ConceptBridge — Pre-Event Assets

From Concept Gaps to Complementary Connections

Team: 404 Brain Not Found
Track: Semantic Matchmaking
Department: Information Technology
Institution: Madras Institute of Technology, Anna University

1. Concept

ConceptBridge is a peer-learning matchmaking system that works at the concept level instead of relying on overall marks or random grouping.

It identifies students whose strengths and gaps are complementary:

A teaches what B needs, and B teaches what A needs.

For the hackathon, the full ConceptBridge vision is reduced to a One-Quiz Reciprocal Match Pilot. This is the smallest end-to-end slice that demonstrates the core idea.

2. Hackathon Pilot

Quiz CSV
   ↓
Concept Profiles
   ↓
Reciprocal Match
   ↓
Human Approval
   ↓
Peer-Learning Session
   ↓
Follow-Up Mini Quiz
   ↓
Learning Gain
   ↓
Profile Update
   ↓
Re-match if ineffective

Input

One quiz CSV

Hand-tagged question → concept mapping

5–8 concepts

Output

Student concept profiles

Reciprocal match + compatibility score

Explainable “Why these two?”

Structured peer-learning session

Learning-gain result

Updated JSON learner state

Re-match when necessary

3. Architecture



The architecture follows the Project Plan / AgentSpec flow: Concept Analysis → Reciprocal Matchmaking → Human Approval → Peer Learning → Outcome Evaluation → Persistent State.

4. Agentic Components

Concept Analysis Agent

Builds concept-level proficiency vectors from quiz results and the question-to-concept mapping.

Reciprocal Matchmaking Agent

Finds a pair with useful knowledge transfer in both directions and explains the match.

Peer Learning Agent

Generates a short two-way teaching plan, prompts, shared challenge, and follow-up mini-quiz.

Outcome Evaluation

Calculates concept-level learning gain and updates learner state. An ineffective outcome can send the workflow back to matchmaking.

The core numerical calculations remain deterministic Python logic; the LLM is used selectively for explanation/session generation.

5. Stateful Workflow

Key states:

Profiling
   ↓
Matching
   ↓
Waiting for Approval
   ↓
Session
   ↓
Evaluation
   ↓
Updated Profile
   ↓
Finished

Backward paths:

Reject approval ─────────→ Matching
Ineffective outcome ─────→ Matching

The pilot is bounded by:

12 model calls per run

2 re-matching attempts

6. Persistent Learner State

The pilot uses JSON rather than a database.

data/
├── students.json
├── concepts.json
├── matches.json
└── sessions.json

The next run reads previous profiles, match history, and outcomes instead of starting from zero.

7. Scope Boundary

Build

CSV ingestion

Hand-tagged concepts

Concept profiling

Reciprocal compatibility

Explainable matching

Human approval

Peer-learning session

Follow-up assessment

Learning gain

Persistent state

Adaptive re-matching

Do Not Build

LMS integration

Automatic concept taxonomy

Multi-course/institution-wide matching

Knowledge graphs

Reinforcement learning

Large dashboards

Complex multi-agent orchestration

8. Two-Day Priority

Phase

Focus

1

State-machine skeleton

2

Real CSV + concept profiles + JSON state

3

Reciprocal matchmaking + explanation + approval

4

Peer learning + outcome + profile update + re-match

5

Demo polish + fallback

The detailed implementation plan, contracts, file responsibilities, limits, and demo checklist remain in the repository's Project Plan.

9. Demo Story

The demo should show:

Upload quiz

Show concept mapping

Generate learner profiles

Show complementary strengths/gaps

Explain why the pair was selected

Approve the match

Generate the peer session

Run the follow-up quiz

Show learning gain

Show updated state / re-matching

The strongest proof point is not simply “A ↔ B”, but:

“A can teach B X, while B can teach A Y — and the system can measure whether that exchange worked.”

10. Previous Agentic AI Work

The team has prior experience with a stateful iterative agent through:

Assignment Improvement Agent
https://github.com/PragadheeshPandian1906/assignment-agent

That project provides relevant experience with:

Explicit state

Iterative evaluation

Persistent records

Bounded execution

Retry/revision loops

It is reference work, not a dependency of ConceptBridge.

11. Future Direction

The same learner-state architecture can later support:

Automatic concept extraction

Real-time assessment ingestion

Group matchmaking

Cross-course profiles

LMS integration

Larger-scale learning analytics

Repository Assets

The repository also includes the Project Plan PDF as a reference for the hackathon implementation.

Project Plan.pdf

Use the PDF for the detailed execution plan, build phases, state-machine contracts, file responsibilities, validation checks, and demo requirements. This document intentionally remains a concise pre-event overview.

Status

🚧 Pre-event — implementation not yet started

Project Plan.pdf: detailed execution reference included in the repository
AgentSpec: project/state-machine specification
This document: concise pre-event overview