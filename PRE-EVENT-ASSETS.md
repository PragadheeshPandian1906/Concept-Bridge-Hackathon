# ConceptBridge — Pre-Event Assets

## From Concept Gaps to Complementary Connections

ConceptBridge is a peer-learning matchmaking system designed to connect students based on **concept-level knowledge gaps and strengths**, rather than marks, random grouping, or broad subject-level performance.

The system profiles each learner from quiz responses, identifies concepts where each student is relatively strong or weak, and finds **reciprocal complementary pairs**:

> **Student A knows what Student B needs, and Student B knows what Student A needs.**

The matched students then participate in a structured peer-learning session. A follow-up assessment measures whether the interaction produced measurable learning gain. The learner profiles are subsequently updated, and unsuccessful matches can trigger a re-matching cycle.

This repository represents the planned **two-day hackathon pilot**: a deliberately small, end-to-end vertical slice that demonstrates the core intelligence of the system without attempting to build a production-scale learning platform.

---

# 1. Team Information

| Field           | Details                                         |
| --------------- | ----------------------------------------------- |
| **Team Name**   | 404 Brain Not Found                             |
| **Track**       | Semantic Matchmaking                            |
| **Department**  | Information Technology                          |
| **Institution** | Madras Institute of Technology, Anna University |

### Team Members

| No. | Name                    | Role        |
| --: | ----------------------- | ----------- |
|   1 | Sanjana V               | Team Leader |
|   2 | Pragadheesh Pandian S P | Team Member |
|   3 | Aishwarya N             | Team Member |

---

# 2. Problem We Are Addressing

Traditional student grouping mechanisms generally rely on:

* Random grouping
* Overall marks
* Class rank
* Subject-level performance
* Self-selected groups
* Manual teacher assignment

These approaches do not necessarily identify **who can teach whom**.

For example:

Consider two students:

* Student A understands **Recursion** well but struggles with **Dynamic Programming**.
* Student B understands **Dynamic Programming** well but struggles with **Recursion**.

Their overall marks may be similar.

A conventional grouping system may treat them as two average-performing students.

ConceptBridge instead identifies:

```text
Student A
    Strong → Recursion
    Weak   → Dynamic Programming

Student B
    Strong → Dynamic Programming
    Weak   → Recursion
```

This creates a potentially reciprocal learning relationship:

```text
Student A ───── teaches ─────> Student B
Student A <──── learns ─────── Student B
```

The objective is therefore not simply:

> "Find students who are similar."

It is:

> **"Find students whose knowledge gaps and strengths complement each other."**

---

# 3. Core Concept

ConceptBridge works at the **concept level** rather than treating the student's overall quiz score as the complete representation of their knowledge.

The pilot starts with a single quiz.

Each question is mapped to one or more concepts.

For example:

| Question | Concept             |
| -------- | ------------------- |
| Q1       | Recursion           |
| Q2       | Recursion           |
| Q3       | Dynamic Programming |
| Q4       | Graph Traversal     |
| Q5       | Graph Traversal     |

Student responses are then converted into concept-level proficiency.

Example:

```text
Student A

Recursion             → 0.90
Dynamic Programming   → 0.35
Graph Traversal       → 0.70
```

Another student may have:

```text
Student B

Recursion             → 0.40
Dynamic Programming   → 0.85
Graph Traversal       → 0.60
```

The system can then identify reciprocal complementarity.

---

# 4. What the Two-Day Pilot Demonstrates

The hackathon implementation intentionally focuses on **one complete vertical slice** rather than building a large platform.

The pilot demonstrates the following flow:

```text
Quiz CSV
   ↓
Question → Concept Mapping
   ↓
Student Responses
   ↓
Concept-Level Profiles
   ↓
Complementary Match
   ↓
Match Explanation
   ↓
Mentor Approval
   ↓
Peer-Learning Session
   ↓
Follow-Up Quiz
   ↓
Learning Gain
   ↓
Profile Update
   ↓
Successful?
   ├── Yes → Persist Updated State
   └── No  → Re-Match
```

The goal is to make this entire cycle demonstrable within the hackathon.

---

# 5. Pilot Scope

## Included

The two-day pilot includes:

1. One quiz dataset
2. Question-to-concept mapping
3. Student response processing
4. Concept-level proficiency calculation
5. Complementary pair discovery
6. Two-way teaching validation
7. Natural-language match explanation
8. Mentor approval
9. Structured peer-learning session generation
10. Follow-up assessment
11. Learning-gain calculation
12. Learner-profile update
13. Re-matching when learning gain is insufficient
14. Persistent JSON state
15. CLI-based demonstration
16. Optional lightweight React/Vite interface if time permits

---

# 6. Deliberately Out of Scope

The pilot does **not** attempt to build:

* A complete Learning Management System
* A multi-semester student database
* Automated curriculum generation
* A large-scale recommendation platform
* Real-time classroom integration
* Complex authentication
* Mobile applications
* Teacher analytics dashboards
* Production deployment infrastructure
* Large-scale distributed architecture
* Automated grading using an LLM
* Fully autonomous educational decisions

The purpose is to prove the **core matchmaking loop** first.

---

# 7. Why Concept-Level Matching?

A student's overall score can hide important differences in understanding.

Consider:

```text
Student A

Concept 1 → 90%
Concept 2 → 40%
Concept 3 → 80%
```

and:

```text
Student B

Concept 1 → 45%
Concept 2 → 90%
Concept 3 → 75%
```

Their total scores may be similar.

However, their concept profiles reveal a stronger reciprocal learning opportunity:

```text
             Concept 1       Concept 2

Student A       Strong          Weak
Student B       Weak            Strong

                ↕                ↕
             Reciprocal Complementarity
```

ConceptBridge therefore treats a learner as a **vector of concept-level strengths and gaps**, rather than a single score.

---

# 8. Matching Principle

The central matching requirement is **two-way complementarity**.

A valid pair should ideally satisfy:

```text
A is strong where B is weak

AND

B is strong where A is weak
```

Conceptually:

```text
              Student A
             /         \
        Strong           Weak
          /               \
    Concept X          Concept Y
          \               /
        Weak            Strong
             \         /
              Student B
```

The system should avoid considering a pair successful merely because:

* They have similar marks
* They are in the same class
* They have similar overall proficiency
* One student is simply much stronger than the other

The focus is reciprocal knowledge exchange.

---

# 9. Learning Loop

The project is not only a matchmaking system.

It contains a feedback loop.

## Initial State

```text
Quiz
 ↓
Concept Profile
 ↓
Match
```

## Learning Interaction

```text
Matched Students
 ↓
Peer-learning Session
 ↓
Follow-up Quiz
```

## Evaluation

```text
Before Performance
        ↓
Peer Learning
        ↓
After Performance
        ↓
Learning Gain
```

## Adaptation

If the learning gain is sufficient:

```text
Update Profile
        ↓
Continue
```

If the learning gain is insufficient:

```text
Evaluate Failed Match
        ↓
Find Another Complementary Partner
        ↓
New Session
```

This feedback loop is one of the important agentic characteristics of the pilot.

---

# 10. Agentic AI Direction

ConceptBridge is designed as a **bounded agentic workflow**, rather than a simple LLM chatbot.

The system has:

* State
* Goals
* Decisions
* Tool/data interactions
* Persistent learner information
* Evaluation
* Feedback
* Retry/recovery
* Termination conditions

The LLM is intentionally not responsible for everything.

For example:

### Deterministic Logic

Used for:

* Quiz scoring
* Concept proficiency calculation
* Learning-gain calculation
* Threshold checks
* State transitions
* Match constraints

### LLM

Used for:

* Explaining why two students complement each other
* Generating a structured peer-learning session
* Converting system information into human-readable guidance

This separation keeps important calculations deterministic while using the LLM where language generation and reasoning are useful.

---

# 11. Planned Agent Flow

The conceptual state machine is:

```text
                    ┌───────────────┐
                    │  Load Quiz    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Build Profiles│
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Find Match    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Explain Match │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Mentor Review │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Learning      │
                    │ Session       │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Follow-up Quiz│
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Evaluate Gain │
                    └───────┬───────┘
                            ↓
                     ┌──────┴──────┐
                     │             │
                  Sufficient    Insufficient
                     │             │
                     ↓             ↓
              Update Profile   Re-Match
                     │             │
                     └──────┬──────┘
                            ↓
                         Finish
```

The exact state definitions, transitions, limits, and implementation contracts will be maintained in the project's **Project Plan** document.

---

# 12. Project Plan

A separate **Project Plan** document will be maintained in the repository.

The Project Plan is the primary implementation reference for:

* Detailed requirements
* Two-day development plan
* State machine
* Data model
* Module responsibilities
* Implementation phases
* Agent behavior
* LLM integration
* Testing strategy
* Demo flow
* Build priorities
* Cut lines if time becomes limited

This `PRE-EVENT-ASSETS.md` provides the **pre-event overview and project context**, while the Project Plan contains the more detailed execution plan.

The implementation should follow the Project Plan rather than expanding the scope unnecessarily during the hackathon.

---

# 13. Previous Agentic AI Work

As technical preparation for this project, the team has previously worked on an agentic-AI project:

**Assignment Improvement Agent**

Repository:

https://github.com/PragadheeshPandian1906/assignment-agent

The project explores a small stateful AI agent that:

```text
Student Answer
      ↓
Evaluation
      ↓
Feedback
      ↓
Revision
      ↓
Re-Evaluation
      ↓
Pass / Retry / Stop
```

The previous work provides useful experience with concepts that are relevant to ConceptBridge, particularly:

* Agent state
* State transitions
* Iterative workflows
* Persistent state
* Bounded model calls
* Evaluation loops
* Revision/retry behavior
* Separation between generic agent infrastructure and domain-specific logic
* Terminal-first agent development

ConceptBridge extends these ideas into a different domain:

```text
Assignment Agent
       │
       ├── Evaluate
       ├── Give Feedback
       ├── Wait for Revision
       └── Re-Evaluate
       
              ↓

ConceptBridge
       │
       ├── Build Learner Profile
       ├── Find Complementary Match
       ├── Explain Match
       ├── Generate Learning Session
       ├── Evaluate Learning Gain
       └── Re-Match
```

The previous repository should therefore be treated as **reference work and architectural experience**, not as a dependency of ConceptBridge.

---

# 14. Relationship Between Previous Work and ConceptBridge

The previous Assignment Agent and ConceptBridge share a common design philosophy:

## Stateful Agent

The system should know:

```text
What has happened?
What is the current state?
What should happen next?
```

## Bounded Execution

The agent should not run indefinitely.

Example constraints may include:

```text
Maximum match attempts
Maximum re-matches
Maximum LLM calls
Maximum learning cycles
```

The exact limits will be defined in the Project Plan.

## Deterministic + LLM Hybrid

The previous work demonstrates that an agent does not need to give every responsibility to an LLM.

ConceptBridge follows the same principle:

```text
                    ConceptBridge
                         │
            ┌────────────┴────────────┐
            │                         │
      Deterministic               LLM
         Logic                    Logic
            │                         │
      Quiz Scoring              Explanation
      Profiles                  Session Generation
      Matching                  Natural Language
      Gain Calculation
      State Control
```

---

# 15. Technology Stack

## Backend

**Python**

Python will contain the main application logic and agent workflow.

---

## Data Input

**CSV**

The pilot will initially use CSV files for:

* Quiz questions
* Student responses
* Question-to-concept mapping

Example:

```text
quiz.csv
concept_mapping.csv
responses.csv
```

---

## Persistent State

**JSON**

The pilot intentionally avoids a database.

Learner state and relevant agent state can be persisted as JSON.

Example:

```text
state/
├── learners.json
├── matches.json
├── sessions.json
└── agent_state.json
```

This keeps the two-day implementation simple and transparent.

---

## LLM

**Claude API**

The LLM is used selectively for language and reasoning tasks such as:

* Match explanations
* Peer-learning session generation

The LLM is **not** the source of truth for:

* Quiz scores
* Concept proficiency
* Learning-gain calculations
* Core matching calculations
* State transitions

---

## Interface

### Primary

CLI

The command-line interface will be the primary demo interface because it allows the core agent workflow to be completed quickly.

### Optional

React + Vite

A lightweight frontend may be added if sufficient development time remains.

The frontend is secondary to completing the end-to-end agent workflow.

---

# 16. High-Level Repository Direction

The expected implementation can evolve toward a structure such as:

```text
conceptbridge/
│
├── data/
│   ├── quiz.csv
│   ├── responses.csv
│   └── concept_mapping.csv
│
├── state/
│   ├── learners.json
│   ├── matches.json
│   └── sessions.json
│
├── app/
│   ├── profile/
│   ├── matching/
│   ├── session/
│   ├── evaluation/
│   ├── agent/
│   └── llm/
│
├── tests/
│
├── cli/
│
├── frontend/
│
├── Project-Plan.md
├── PRE-EVENT-ASSETS.md
└── README.md
```

The actual structure should be finalized according to the Project Plan and implementation needs rather than following this example rigidly.

---

# 17. Expected Core Components

## 17.1 Quiz Loader

Responsible for reading the quiz and student response data.

```text
CSV
 ↓
Validated Records
```

---

## 17.2 Concept Mapper

Associates questions with concepts.

```text
Question
 ↓
Concept
```

For example:

```text
Q1 → Recursion
Q2 → Recursion
Q3 → Dynamic Programming
```

---

## 17.3 Learner Profiler

Converts question-level responses into concept-level proficiency.

```text
Responses
    ↓
Question Scores
    ↓
Concept Aggregation
    ↓
Learner Profile
```

---

## 17.4 Match Engine

Identifies complementary students.

The matching engine should consider:

* Student strengths
* Student weaknesses
* Reciprocal complementarity
* Concept overlap
* Minimum evidence requirements
* Existing pairing/session history

---

## 17.5 Match Explanation

The LLM converts the structured match information into a human-readable explanation.

Example:

```text
Student A is strong in recursion but needs support in
dynamic programming.

Student B demonstrates stronger performance in dynamic
programming while having a gap in recursion.

They therefore have complementary learning needs.
```

The explanation should be grounded in the calculated profile data.

---

## 17.6 Mentor Approval

The pilot includes a human checkpoint.

```text
System proposes match
        ↓
Human reviews explanation
        ↓
Approve / Reject
```

This keeps the prototype human-supervised rather than fully autonomous.

---

## 17.7 Session Generator

The LLM generates a short structured peer-learning plan.

A session may contain:

```text
1. Topic A → Student A teaches Student B
2. Topic B → Student B teaches Student A
3. Short discussion
4. Practice questions
5. Reflection
```

The generated session should be constrained by the actual concept profile.

---

## 17.8 Outcome Evaluator

The system compares pre-session and post-session performance.

Conceptually:

```text
Learning Gain =
Post-Session Performance - Pre-Session Performance
```

The exact calculation and thresholds will be specified in the Project Plan.

---

## 17.9 Profile Updater

The student's persistent profile is updated using the outcome.

```text
Old Profile
    ↓
Learning Session
    ↓
Follow-up Assessment
    ↓
Updated Profile
```

---

## 17.10 Re-Matching

If the session does not produce sufficient learning gain, the system should not blindly repeat the same interaction.

Instead:

```text
Insufficient Gain
       ↓
Record Failed Match
       ↓
Search Remaining Candidates
       ↓
Generate New Match
       ↓
New Learning Session
```

The Project Plan will define the termination conditions so that this process remains bounded.

---

# 18. Example End-to-End Scenario

Assume there are four students:

```text
A
B
C
D
```

The quiz contains concepts:

```text
C1 = Recursion
C2 = Dynamic Programming
C3 = Graphs
C4 = Sorting
```

After scoring:

```text
A:
C1 → Strong
C2 → Weak
C3 → Medium
C4 → Strong

B:
C1 → Weak
C2 → Strong
C3 → Medium
C4 → Medium
```

The system identifies:

```text
A → can teach C1 → B
B → can teach C2 → A
```

Therefore:

```text
A ↔ B
```

The system generates an explanation and requests mentor approval.

After approval:

```text
A teaches B:
Recursion

B teaches A:
Dynamic Programming
```

A follow-up quiz is conducted.

Suppose:

```text
A:
Dynamic Programming
Before → 40%
After  → 70%

B:
Recursion
Before → 45%
After  → 75%
```

The system records the learning gain and updates both profiles.

The students may now have different gaps.

Therefore, future matching can use the **updated state**, rather than the original quiz alone.

---

# 19. What Makes the Pilot Agentic?

The system is intended to demonstrate more than a static recommendation.

The agent:

```text
OBSERVE
   ↓
UNDERSTAND STATE
   ↓
DECIDE
   ↓
ACT
   ↓
EVALUATE
   ↓
UPDATE STATE
   ↓
DECIDE AGAIN
```

For ConceptBridge:

```text
Observe:
Student quiz responses

Understand:
Concept-level learner profiles

Decide:
Which pair is complementary?

Act:
Create a peer-learning session

Evaluate:
Did learning improve?

Update:
Modify learner state

Decide again:
Should the students continue or should the system re-match?
```

This feedback loop is the central agentic behavior of the project.

---

# 20. Human-in-the-Loop Design

The pilot intentionally includes a mentor approval stage.

The system should not silently create and execute every match.

Instead:

```text
Agent
 ↓
Match Proposal
 ↓
Human Review
 ↓
Approved?
 ├── Yes → Continue
 └── No  → Find another match
```

This provides an explicit control point and makes the prototype easier to demonstrate and inspect.

---

# 21. Design Principles

The implementation should follow these principles.

### 1. Deterministic Where Possible

Use normal code for calculations and rules.

### 2. LLM Where Useful

Use the LLM for language generation and contextual reasoning rather than simple arithmetic.

### 3. State Is Explicit

The current agent state should be visible and persistable.

### 4. Every Decision Should Have Evidence

A match should be explainable using concept-level data.

### 5. Bounded Agent

The agent must have limits on retries, matching attempts, and model usage.

### 6. Human Oversight

The pilot should allow mentor approval before the learning session.

### 7. Small Vertical Slice

Complete one end-to-end workflow before adding extra features.

### 8. Demoability

Every major step should be observable during the final demonstration.

---

# 22. Two-Day Development Philosophy

The project should be developed vertically rather than building isolated components for the entire system.

The preferred progression is:

```text
Day 1
─────
Data
 ↓
Profiles
 ↓
Matching
 ↓
Basic Agent State
 ↓
CLI End-to-End Skeleton
```

Then:

```text
Day 2
─────
LLM Integration
 ↓
Match Explanation
 ↓
Session Generation
 ↓
Follow-Up Evaluation
 ↓
Profile Update
 ↓
Re-Matching
 ↓
Demo Polish
```

The detailed hour-by-hour plan, milestones, cut lines, and implementation priorities are maintained in the **Project Plan**.

---

# 23. Pre-Event Preparation Checklist

Before the event, the team should have the following ready:

* [ ] Repository initialized
* [ ] Project Plan available
* [ ] PRE-EVENT-ASSETS.md available
* [ ] Sample quiz CSV
* [ ] Question-to-concept mapping
* [ ] Sample student responses
* [ ] Python environment
* [ ] Dependencies identified
* [ ] Claude API access verified
* [ ] Previous Assignment Agent repository reviewed
* [ ] Basic architecture understood
* [ ] Initial state-machine design understood
* [ ] Demo scenario prepared

The goal of pre-event preparation is to remove setup uncertainty so that the hackathon can focus on implementation.

---

# 24. Definition of a Successful Hackathon Pilot

The pilot can be considered complete when the team can demonstrate:

```text
1. Load quiz
        ↓
2. Build concept profiles
        ↓
3. Find reciprocal match
        ↓
4. Explain why the pair was selected
        ↓
5. Obtain mentor approval
        ↓
6. Generate peer-learning session
        ↓
7. Run / simulate follow-up quiz
        ↓
8. Calculate learning gain
        ↓
9. Update learner state
        ↓
10. Re-match when necessary
```

The final demonstration should show the system moving through this complete cycle rather than only showing isolated features.

---

# 25. Future Expansion

The hackathon pilot intentionally starts with one quiz.

A future version could expand to:

```text
Multiple Quizzes
        ↓
Continuous Learner Profiles
        ↓
More Concepts
        ↓
Historical Learning Data
        ↓
Better Match Optimization
        ↓
Repeated Peer-Learning Cycles
```

Potential future capabilities include:

* Multi-subject learner profiles
* Historical concept mastery
* Match-quality tracking
* Long-term learning trajectories
* Group matchmaking
* Teacher dashboards
* Concept dependency graphs
* Adaptive quizzes
* Match success analytics
* Learning-community formation
* Larger-scale recommendation infrastructure

These features are **future directions**, not requirements for the two-day pilot.

---

# 26. Important Scope Boundary

The project should not become a generic:

> "AI education platform."

The core hackathon story should remain:

> **ConceptBridge finds students who can teach each other based on complementary concept-level knowledge, validates the interaction through a follow-up assessment, updates their learner state, and adapts the next match when necessary.**

Everything implemented during the hackathon should support this central loop.

---

# 27. Key Demo Narrative

The final demonstration should communicate one simple story:

### Before

```text
We know students' quiz answers,
but not who can help whom.
```

### Intelligence

```text
ConceptBridge converts answers
into concept-level learner profiles.
```

### Match

```text
A is strong where B is weak.

B is strong where A is weak.

Therefore:
A ↔ B
```

### Action

```text
The system generates
a reciprocal peer-learning session.
```

### Evidence

```text
A follow-up quiz measures
whether learning actually occurred.
```

### Adaptation

```text
If it worked:
    update learner profiles.

If it didn't:
    find another complementary match.
```

### Final Message

```text
ConceptBridge does not simply group students.

It creates,
tests,
and adapts
peer-learning connections.
```

---

# 28. Repository References

### Project Repository

The ConceptBridge repository contains the implementation, project documentation, data, and hackathon assets.

### Project Plan

The `Project Plan` document is the detailed implementation reference for the two-day hackathon.

It should be consulted for:

* Exact requirements
* Development order
* State machine
* Data contracts
* Module responsibilities
* Agent limits
* Testing
* Demo requirements
* Cut lines

### Previous Agentic AI Work

**Assignment Improvement Agent**

Repository:

https://github.com/PragadheeshPandian1906/assignment-agent

This project serves as prior technical reference for stateful agent workflows, iterative evaluation, persistent state, and bounded agent behavior.

---

# 29. Final Pre-Event Summary

ConceptBridge is a focused two-day pilot for **semantic peer-learning matchmaking**.

It starts with:

```text
Quiz Data
```

and transforms it into:

```text
Concept-Level Learner Profiles
```

which are used to create:

```text
Reciprocal Student Matches
```

The matched students then participate in:

```text
Structured Peer Learning
```

The system evaluates:

```text
Learning Gain
```

and uses the result to:

```text
Update State
        or
Re-Match
```

The project combines:

```text
Deterministic Data Processing
            +
Semantic Matchmaking
            +
LLM-Assisted Reasoning
            +
Stateful Agent Workflow
            +
Human-in-the-Loop Approval
            +
Outcome-Based Adaptation
```

The hackathon objective is not to build a complete educational platform.

It is to prove one compelling idea end-to-end:

> **If we understand what students know at the concept level, we can connect complementary learners, let them teach each other, measure whether the interaction worked, and adapt the next connection based on the result.**

---

## Status

🚧 **Pre-event / Not yet implemented**

The implementation will begin during the hackathon according to the project's **Project Plan**.

**Team 404 Brain Not Found**
**Semantic Matchmaking Track**
**Madras Institute of Technology, Anna University**
