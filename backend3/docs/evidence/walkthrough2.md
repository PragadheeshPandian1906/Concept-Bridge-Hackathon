# Walkthrough 2

## Date
19 September 2026

## Tester
3rd Year Information Technology Student

## Objective
Evaluate the robustness of ConceptBridge's peer-learning model and identify limitations in the proposed matching strategy.

## Task Given
1. Review the ConceptBridge workflow.
2. Understand the concept profiling process.
3. Analyze the reciprocal peer-matching mechanism.
4. Evaluate whether the system can effectively support different class sizes and learning scenarios.

## Observations
- The tester understood the concept-level profiling approach.
- The tester understood how reciprocal peer matches were generated.
- The tester questioned how the system would behave when the cohort contains an odd number of students.
- The tester observed that pair-based matching alone may not fully utilize all available knowledge within a class.
- The tester found the CLI-based interaction difficult to follow during testing and suggested a more visual interface.

## Feedback
> "What happens if there is an odd number of students? One student may be left unmatched."

> "It would be easier to understand and test if there was a visual interface instead of only CLI output."

## Analysis
The feedback highlighted a limitation in the initial design.

While reciprocal peer matching successfully identifies complementary pairs, it does not capture the broader flow of knowledge across an entire cohort. In odd-sized cohorts, some students may not be included in a pair despite having valuable knowledge-transfer opportunities.

The CLI output also made it difficult to visualize relationships between students and concepts.

## Action Taken
The team introduced the **Knowledge Transfer Graph (KTG)**.

### Knowledge Transfer Graph (KTG)

- Students are represented as nodes.
- Knowledge-transfer opportunities are represented as directed edges.
- Each edge corresponds to a specific concept.
- Edge weights indicate the strength of the transfer opportunity.

Example:

- Student A → Student B (Recursion)
- Student B → Student C (SQL Joins)
- Student C → Student D (Trees)

The graph enables:
- Identification of alternative learning opportunities.
- Better handling of odd-sized cohorts.
- Visualization of knowledge flow within the class.
- Detection of knowledge hubs and isolated learners.
- Support for future group-learning recommendations.

Additionally, the team initiated frontend development to replace CLI-only interaction and improve usability, explainability, and testing.

## Result
The project evolved from a pair-focused recommendation system into a cohort-level knowledge-transfer framework.

The Knowledge Transfer Graph provides:
- Greater flexibility in matching.
- Improved explainability.
- Better support for complex classroom scenarios.

Frontend development was prioritized to make the system easier for mentors and students to understand and use.

## Status
PASS – Feedback resulted in a significant architectural improvement and UI enhancement roadmap.