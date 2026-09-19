"""MATCHING - deterministic reciprocal compatibility.

This is the algorithmic heart of ConceptBridge, and it contains no model
calls at all. An LLM may later *explain* a candidate; it can never
compute, re-rank or alter one.

Eligibility
-----------
A teaches B on concept c when::

    A[c] >= STRENGTH_THRESHOLD  and  B[c] < GAP_THRESHOLD

A pair is a candidate only if BOTH directions teach at least one concept
(true reciprocity - two strong students are not a match, and a one-way
tutor pairing is not a match).

Score
-----
    a_to_b_score = sum(A[c] - B[c] for c in a_teaches)      # gap closed
    b_to_a_score = sum(B[c] - A[c] for c in b_teaches)
    total        = a_to_b_score + b_to_a_score
    balance      = 1 - |a_to_b_score - b_to_a_score| / total    in [0, 1]

    compatibility = clamp(total / IDEAL_TOTAL_GAP, 0, 1)
                    * (0.5 + 0.5 * balance)

``IDEAL_TOTAL_GAP`` (2.5) is roughly "four concepts of ~0.6 gap each":
the point at which extra gap stops adding value. The balance factor
rewards pairs that help each other equally, and is floored at 0.5 so a
lopsided-but-real reciprocal pair still scores.
"""

from __future__ import annotations

from .schema import MatchCandidate, MatchCandidates, StudentProfile

STRENGTH_THRESHOLD = 0.70
GAP_THRESHOLD = 0.60
IDEAL_TOTAL_GAP = 2.5
MIN_COMPATIBILITY = 0.05


def match_id_for(student_a: str, student_b: str) -> str:
    """Order-independent identity for a pair, e.g. ``S1|S2``."""
    return "|".join(sorted([student_a, student_b]))


def can_teach(teacher: StudentProfile, learner: StudentProfile, concept: str,
              strength: float = STRENGTH_THRESHOLD,
              gap: float = GAP_THRESHOLD) -> bool:
    return teacher.score_for(concept) >= strength and learner.score_for(concept) < gap


def strengths(profile: StudentProfile, strength: float = STRENGTH_THRESHOLD) -> list[str]:
    return [c.concept for c in profile.concepts if c.score >= strength]


def gaps(profile: StudentProfile, gap: float = GAP_THRESHOLD) -> list[str]:
    return [c.concept for c in profile.concepts if c.score < gap]


def teachable_concepts(teacher: StudentProfile, learner: StudentProfile,
                       strength: float = STRENGTH_THRESHOLD,
                       gap: float = GAP_THRESHOLD) -> list[str]:
    """Concepts `teacher` can usefully teach `learner`, best gap first."""
    useful = [
        (teacher.score_for(c.concept) - learner.score_for(c.concept), c.concept)
        for c in teacher.concepts
        if can_teach(teacher, learner, c.concept, strength, gap)
    ]
    useful.sort(key=lambda item: (-item[0], item[1]))
    return [concept for _, concept in useful]


def primary_concept(teacher: StudentProfile, learner: StudentProfile,
                    concepts: list[str]) -> str | None:
    """The concept a session focuses on: the largest gap in that direction."""
    if not concepts:
        return None
    return max(concepts,
               key=lambda c: (teacher.score_for(c) - learner.score_for(c), c))


def score_pair(a: StudentProfile, b: StudentProfile,
               strength: float = STRENGTH_THRESHOLD,
               gap: float = GAP_THRESHOLD) -> MatchCandidate | None:
    """Return a scored candidate, or None when the pair is not reciprocal."""
    a_teaches = teachable_concepts(a, b, strength, gap)
    b_teaches = teachable_concepts(b, a, strength, gap)
    if not a_teaches or not b_teaches:
        return None

    a_to_b = sum(a.score_for(c) - b.score_for(c) for c in a_teaches)
    b_to_a = sum(b.score_for(c) - a.score_for(c) for c in b_teaches)
    total = a_to_b + b_to_a
    if total <= 0:
        return None

    balance = 1.0 - abs(a_to_b - b_to_a) / total
    coverage = min(1.0, total / IDEAL_TOTAL_GAP)
    compatibility = round(coverage * (0.5 + 0.5 * balance), 4)

    rationale = (
        f"{a.student_name} can teach {', '.join(a_teaches)}; "
        f"{b.student_name} can teach {', '.join(b_teaches)}. "
        f"Gap closed {a_to_b:.2f} one way and {b_to_a:.2f} the other "
        f"(balance {balance:.2f})."
    )
    return MatchCandidate(
        match_id=match_id_for(a.student_id, b.student_id),
        student_a=a.student_id,
        student_b=b.student_id,
        compatibility_score=compatibility,
        a_teaches=a_teaches,
        b_teaches=b_teaches,
        rationale=rationale,
        a_to_b_score=round(a_to_b, 4),
        b_to_a_score=round(b_to_a, 4),
        balance=round(balance, 4),
    )


def generate_candidates(profiles: list[StudentProfile],
                        excluded: list[str] | set[str] | None = None,
                        strength: float = STRENGTH_THRESHOLD,
                        gap: float = GAP_THRESHOLD) -> MatchCandidates:
    """All eligible pairs, best first. Excluded match_ids are dropped."""
    excluded = set(excluded or ())
    by_id = sorted(profiles, key=lambda p: p.student_id)
    items: list[MatchCandidate] = []

    for i in range(len(by_id)):
        for j in range(i + 1, len(by_id)):
            a, b = by_id[i], by_id[j]
            if match_id_for(a.student_id, b.student_id) in excluded:
                continue
            candidate = score_pair(a, b, strength, gap)
            if candidate and candidate.compatibility_score >= MIN_COMPATIBILITY:
                items.append(candidate)

    # deterministic ordering: score desc, then match_id asc
    items.sort(key=lambda c: (-c.compatibility_score, c.match_id))
    return MatchCandidates(items=items)


def best_candidate(profiles: list[StudentProfile],
                   excluded: list[str] | set[str] | None = None) -> MatchCandidate | None:
    candidates = generate_candidates(profiles, excluded)
    return candidates.items[0] if candidates.items else None


def fallback_explanation(candidate: MatchCandidate,
                         a: StudentProfile, b: StudentProfile) -> str:
    """Deterministic explanation used when the LLM is unavailable or fails."""
    lines = [
        f"{a.student_name} and {b.student_name} are a reciprocal match "
        f"(compatibility {candidate.compatibility_score:.2f}).",
    ]
    for teacher, learner, concepts in (
        (a, b, candidate.a_teaches), (b, a, candidate.b_teaches)
    ):
        for concept in concepts:
            lines.append(
                f"- {teacher.student_name} scored {teacher.score_for(concept):.2f} "
                f"on {concept} where {learner.student_name} scored "
                f"{learner.score_for(concept):.2f}."
            )
    lines.append("Each student therefore has something to teach and something to learn.")
    return "\n".join(lines)
