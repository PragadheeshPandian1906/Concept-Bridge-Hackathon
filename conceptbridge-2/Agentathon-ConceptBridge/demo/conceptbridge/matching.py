from __future__ import annotations

from itertools import combinations

from .profiling import profile_map
from .schema import MatchCandidate, MatchCandidates, StudentProfile

STRENGTH_THRESHOLD = 0.70
GAP_THRESHOLD = 0.60


def _candidate(a: StudentProfile, b: StudentProfile) -> MatchCandidate | None:
    am, bm = profile_map(a), profile_map(b)
    a_teaches = sorted(c for c in am if am[c] >= STRENGTH_THRESHOLD and bm[c] < GAP_THRESHOLD)
    b_teaches = sorted(c for c in bm if bm[c] >= STRENGTH_THRESHOLD and am[c] < GAP_THRESHOLD)
    if not a_teaches or not b_teaches:
        return None
    a_to_b = sum(am[c] - bm[c] for c in a_teaches)
    b_to_a = sum(bm[c] - am[c] for c in b_teaches)
    score = min(1.0, ((a_to_b / len(a_teaches)) + (b_to_a / len(b_teaches))) / 2)
    match_id = "-".join(sorted((a.student_id, b.student_id)))
    return MatchCandidate(
        match_id=match_id,
        student_a=a.student_id,
        student_b=b.student_id,
        compatibility_score=round(score, 6),
        a_teaches=a_teaches,
        b_teaches=b_teaches,
        rationale=(f"{a.student_name} can teach {', '.join(a_teaches)} while "
               f"{b.student_name} can teach {', '.join(b_teaches)}. "
               "The compatibility score is computed from both directional gaps."),
        score_components={"a_to_b": round(a_to_b, 6), "b_to_a": round(b_to_a, 6)},
    )


def find_candidates(profiles: list[StudentProfile], excluded: set[str] | None = None) -> MatchCandidates:
    excluded = excluded or set()
    items = []
    for a, b in combinations(sorted(profiles, key=lambda p: p.student_id), 2):
        candidate = _candidate(a, b)
        if candidate and candidate.match_id not in excluded:
            items.append(candidate)
    items.sort(key=lambda item: (-item.compatibility_score, item.match_id))
    return MatchCandidates(items=items)