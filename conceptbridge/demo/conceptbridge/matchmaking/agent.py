"""Agent 2 - Matchmaking: 'who can teach whom, about what?'

This agent NEVER calls an LLM. Every number it produces is explainable.
"""
from __future__ import annotations

import uuid
from itertools import combinations

from sqlalchemy.orm import Session as DBSession

from ..config import DomainConfig, get_config
from ..persistence.models import Concept, EdgeStat, MatchCandidate
from ..schema import GroupCandidate, GroupProperties, Relationship
from . import graph as G


def _relationships(db: DBSession, members: list[str]) -> list[Relationship]:
    names = {c.id: c.name for c in db.query(Concept).all()}
    rels: list[Relationship] = []
    for edge in G.edges(db):
        if edge["source"] in members and edge["target"] in members:
            for concept in edge["concepts"]:
                rels.append(
                    Relationship(
                        teacher=edge["source"],
                        learner=edge["target"],
                        concept_id=concept["concept_id"],
                        concept=names.get(concept["concept_id"], concept["concept_id"]),
                        teacher_score=concept["teacher_score"],
                        learner_score=concept["learner_score"],
                        gap=concept["transfer_gap"],
                    )
                )
    return rels


def _previous_match_count(db: DBSession, members: list[str]) -> float:
    counts = []
    for a, b in combinations(sorted(members), 2):
        n = (
            db.query(EdgeStat)
            .filter(EdgeStat.source_student.in_([a, b]), EdgeStat.target_student.in_([a, b]))
            .count()
        )
        sessions = sum(
            s.sessions
            for s in db.query(EdgeStat)
            .filter(EdgeStat.source_student.in_([a, b]), EdgeStat.target_student.in_([a, b]))
            .all()
        )
        counts.append(sessions if n else 0)
    return sum(counts) / len(counts) if counts else 0.0


def _observed_effectiveness(db: DBSession, rels: list[Relationship]) -> float:
    values = []
    for rel in rels:
        stat = (
            db.query(EdgeStat)
            .filter(
                EdgeStat.source_student == rel.teacher,
                EdgeStat.target_student == rel.learner,
                EdgeStat.concept_id == rel.concept_id,
            )
            .one_or_none()
        )
        if stat and stat.sessions:
            values.append(stat.successful_sessions / stat.sessions)
    return round(sum(values) / len(values), 4) if values else 0.5  # neutral prior


def score_group(db: DBSession, members: list[str], cfg: DomainConfig | None = None) -> GroupCandidate | None:
    cfg = cfg or get_config()
    rels = _relationships(db, members)
    if not rels:
        return None

    vectors = G.profiles(db)
    loads = G.teaching_load(db)

    # Coverage: of all member gaps, how many does this group actually cover?
    member_gaps = {
        (s, c)
        for s in members
        for c, score in vectors.get(s, {}).items()
        if score < cfg.gap_threshold
    }
    covered = {(r.learner, r.concept_id) for r in rels}
    coverage = len(covered & member_gaps) / len(member_gaps) if member_gaps else 1.0

    directed = {(r.teacher, r.learner) for r in rels}
    reciprocal = sum(1 for a, b in combinations(sorted(members), 2) if (a, b) in directed and (b, a) in directed)
    possible_pairs = max(1, len(members) * (len(members) - 1) // 2)
    reciprocity = reciprocal / possible_pairs

    transfer_strength = sum(r.gap for r in rels) / len(rels)

    teacher_loads = [loads.get(m, 0) for m in members]
    fairness = 1.0 - (sum(teacher_loads) / len(members)) / max(1, cfg.max_teaching_load)
    fairness = max(0.0, min(1.0, fairness))
    load_penalty = sum(1 for load in teacher_loads if load >= cfg.max_teaching_load) / len(members)

    effectiveness = _observed_effectiveness(db, rels)
    prev = _previous_match_count(db, members)
    prev_penalty = min(1.0, prev / 3.0)

    is_cycle = len(members) >= 3 and all(
        any(r.teacher == m for r in rels) and any(r.learner == m for r in rels) for m in members
    )

    w = cfg.weights
    components = {
        "coverage": round(coverage, 4),
        "reciprocity": round(reciprocity, 4),
        "transfer_strength": round(transfer_strength, 4),
        "fairness": round(fairness, 4),
        "observed_effectiveness": effectiveness,
        "previous_match_penalty": round(prev_penalty, 4),
        "teaching_load_penalty": round(load_penalty, 4),
    }
    score = (
        w["coverage"] * coverage
        + w["reciprocity"] * reciprocity
        + w["transfer_strength"] * transfer_strength
        + w["fairness"] * fairness
        + w["observed_effectiveness"] * effectiveness
        - w["previous_match_penalty"] * prev_penalty
        - w["teaching_load_penalty"] * load_penalty
    )

    return GroupCandidate(
        members=sorted(members),
        relationships=rels,
        properties=GroupProperties(
            knowledge_cycle=is_cycle,
            reciprocal_relationships=reciprocal,
            knowledge_coverage=round(coverage, 4),
            fairness_score=round(fairness, 4),
            observed_effectiveness=effectiveness,
            previous_match_penalty=round(prev_penalty, 4),
            teaching_load_penalty=round(load_penalty, 4),
        ),
        score=round(score, 4),
        components=components,
    )


def candidate_groups(db: DBSession, student_ids: list[str] | None = None) -> list[GroupCandidate]:
    cfg = get_config()
    allowed = set(student_ids) if student_ids else None
    seen: set[tuple[str, ...]] = set()
    candidates: list[GroupCandidate] = []

    def consider(members: list[str]) -> None:
        members = sorted(set(members))
        if len(members) < cfg.min_group_size or len(members) > cfg.max_group_size:
            return
        if allowed and not set(members) <= allowed:
            return
        key = tuple(members)
        if key in seen:
            return
        seen.add(key)
        candidate = score_group(db, members, cfg)
        if candidate:
            candidates.append(candidate)

    # pairs from every active edge, reciprocal pairs, and detected cycles
    for edge in G.edges(db):
        consider([edge["source"], edge["target"]])
    for pair in G.reciprocal_pairs(db):
        consider(pair["students"])
    for cycle in G.find_cycles(db):
        consider(cycle)

    return sorted(candidates, key=lambda c: -c.score)


def propose_match(
    db: DBSession, run_id: str, student_ids: list[str] | None = None, exclude: list[list[str]] | None = None
) -> MatchCandidate | None:
    """Return the best candidate as a persisted, explainable proposal, or None."""
    excluded = {tuple(sorted(g)) for g in (exclude or [])}
    for candidate in candidate_groups(db, student_ids):
        if tuple(candidate.members) in excluded:
            continue
        match = MatchCandidate(
            id=f"MATCH-{uuid.uuid4().hex[:8].upper()}",
            run_id=run_id,
            members=candidate.members,
            relationships=[r.model_dump() for r in candidate.relationships],
            properties=candidate.properties.model_dump(),
            components=candidate.components,
            score=candidate.score,
            status="PROPOSED",
        )
        db.add(match)
        db.commit()
        return match
    return None
