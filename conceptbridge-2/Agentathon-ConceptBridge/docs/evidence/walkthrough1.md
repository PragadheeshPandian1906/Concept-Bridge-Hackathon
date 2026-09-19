# Walkthrough 1

## Date
19 September 2026

## Tester
3rd Year Information Technology Student (one member from another team)

## Objective
Evaluate whether a user can understand ConceptBridge's concept profiling and peer-match recommendation process without additional explanation.

## Task Given
1. Generate student concept profiles from the quiz data.
2. Review the generated profiles.
3. Generate a peer-learning match recommendation.
4. Interpret the matchmaking result.

## Observations
- The tester quickly understood the concept-level student profiles.
- The tester was able to identify student strengths and weaknesses from the generated profiles.
- The tester was confused by the compatibility score shown in the matchmaking output.
- The tester expected a clearer explanation for why a particular pair was selected.

## Feedback
> "The score is shown, but I don't know why these students were matched."

## Analysis
The system generated a compatibility score, but the reasoning behind the recommendation was not sufficiently visible to the user. While the numerical score indicated match quality, it did not clearly communicate the underlying knowledge-transfer opportunities between students.

## Action Taken
The team added a rationale section to the matchmaking output.

The rationale now explicitly displays:
- Concepts Student A can teach Student B.
- Concepts Student B can teach Student A.
- The reason the pair was selected.
- The complementary strengths and weaknesses used in the recommendation.

## Result
The matchmaking process became more transparent and explainable.

Users can now understand:
- Why a match was selected.
- What knowledge transfer is expected.
- How the compatibility score relates to concept-level strengths and gaps.

## Status
PASS – Feedback successfully incorporated into the system.