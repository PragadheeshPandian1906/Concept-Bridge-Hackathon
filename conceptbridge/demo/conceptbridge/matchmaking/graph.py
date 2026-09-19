"""The knowledge-transfer graph: 'what transfer opportunities exist right now?'

Fully deterministic. An edge A -> B means A is strong in a concept where B has a
meaningful gap. It does NOT mean A has already taught B.
"""
from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from ..config import DomainConfig, get_config
from ..persistence.models import Concept, ConceptScore, EdgeConcept, EdgeStat, KnowledgeEdge, Student


def profiles(db: DBSession) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {s.id: {} for s in db.query(Student).all()}
    for row in db.query(ConceptScore).all():
        out.setdefault(row.student_id, {})[row.concept_id] = float(row.score)
    return out


def build_graph(db: DBSession, cfg: DomainConfig | None = None) -> dict:
    """Recompute the CURRENT graph from the CURRENT profiles.

    Historical records (edge_stats, match history, learning gains) are never touched.
    """
    cfg = cfg or get_config()
    vectors = profiles(db)

    # Wipe only the current-graph projection.
    db.query(EdgeConcept).delete()
    db.query(KnowledgeEdge).delete()
    db.commit()

    created = 0
    for teacher, t_scores in vectors.items():
        for learner, l_scores in vectors.items():
            if teacher == learner:
                continue
            concepts = []
            for concept_id, t_score in t_scores.items():
                l_score = l_scores.get(concept_id, 0.0)
                gap = t_score - l_score
                if (
                    t_score >= cfg.strength_threshold
                    and l_score < cfg.gap_threshold
                    and gap >= cfg.min_transfer_gap
                ):
                    concepts.append((concept_id, t_score, l_score, round(gap, 4)))
            if not concepts:
                continue
            edge_score = round(sum(c[3] for c in concepts) / len(concepts), 4)
            edge = KnowledgeEdge(
                source_student=teacher, target_student=learner, active=True, edge_score=edge_score
            )
            db.add(edge)
            db.flush()
            for concept_id, t_score, l_score, gap in concepts:
                db.add(
                    EdgeConcept(
                        edge_id=edge.id,
                        concept_id=concept_id,
                        teacher_score=round(t_score, 4),
                        learner_score=round(l_score, 4),
                        transfer_gap=gap,
                    )
                )
            created += 1
    db.commit()
    return {"edges": created, "students": len(vectors)}


def edges(db: DBSession) -> list[dict]:
    out = []
    for edge in db.query(KnowledgeEdge).filter(KnowledgeEdge.active.is_(True)).all():
        concepts = db.query(EdgeConcept).filter(EdgeConcept.edge_id == edge.id).all()
        out.append(
            {
                "id": edge.id,
                "source": edge.source_student,
                "target": edge.target_student,
                "edge_score": edge.edge_score,
                "concepts": [
                    {
                        "concept_id": c.concept_id,
                        "teacher_score": c.teacher_score,
                        "learner_score": c.learner_score,
                        "transfer_gap": c.transfer_gap,
                    }
                    for c in concepts
                ],
            }
        )
    return out


def adjacency(db: DBSession) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {s.id: set() for s in db.query(Student).all()}
    for edge in db.query(KnowledgeEdge).filter(KnowledgeEdge.active.is_(True)).all():
        adj.setdefault(edge.source_student, set()).add(edge.target_student)
    return adj


def reciprocal_pairs(db: DBSession) -> list[dict]:
    adj = adjacency(db)
    seen: set[tuple[str, str]] = set()
    pairs = []
    for a, targets in adj.items():
        for b in targets:
            if a in adj.get(b, set()):
                key = tuple(sorted((a, b)))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append({"students": list(key), "a_to_b": _concepts(db, a, b), "b_to_a": _concepts(db, b, a)})
    return pairs


def _concepts(db: DBSession, source: str, target: str) -> list[str]:
    edge = (
        db.query(KnowledgeEdge)
        .filter(
            KnowledgeEdge.source_student == source,
            KnowledgeEdge.target_student == target,
            KnowledgeEdge.active.is_(True),
        )
        .one_or_none()
    )
    if edge is None:
        return []
    return [c.concept_id for c in db.query(EdgeConcept).filter(EdgeConcept.edge_id == edge.id).all()]


def find_cycles(db: DBSession, max_size: int | None = None, limit: int = 200) -> list[list[str]]:
    """Simple directed cycles of length 3..max_size (deduplicated by rotation)."""
    cfg = get_config()
    max_size = max_size or cfg.max_group_size
    adj = adjacency(db)
    found: set[tuple[str, ...]] = set()

    def canonical(path: list[str]) -> tuple[str, ...]:
        i = path.index(min(path))
        return tuple(path[i:] + path[:i])

    def walk(start: str, node: str, path: list[str]) -> None:
        if len(found) >= limit:
            return
        for nxt in sorted(adj.get(node, set())):
            if nxt == start and len(path) >= 3:
                found.add(canonical(path))
            elif nxt not in path and len(path) < max_size:
                walk(start, nxt, path + [nxt])

    for student in sorted(adj):
        walk(student, student, [student])
    return [list(c) for c in sorted(found)]


def knowledge_hubs(db: DBSession, cfg: DomainConfig | None = None) -> list[dict]:
    cfg = cfg or get_config()
    adj = adjacency(db)
    hubs = [
        {"student_id": s, "out_degree": len(t), "teaches": sorted(t)}
        for s, t in adj.items()
        if len(t) >= cfg.hub_out_degree
    ]
    return sorted(hubs, key=lambda h: -h["out_degree"])


def concept_bottlenecks(db: DBSession, cfg: DomainConfig | None = None) -> list[dict]:
    cfg = cfg or get_config()
    vectors = profiles(db)
    out = []
    for concept in db.query(Concept).all():
        learners = [s for s, v in vectors.items() if v.get(concept.id, 0.0) < cfg.gap_threshold]
        teachers = [s for s, v in vectors.items() if v.get(concept.id, 0.0) >= cfg.strength_threshold]
        if learners and (not teachers or len(learners) / max(1, len(teachers)) >= cfg.bottleneck_ratio):
            out.append(
                {
                    "concept_id": concept.id,
                    "concept": concept.name,
                    "learners": len(learners),
                    "teachers": len(teachers),
                    "ratio": round(len(learners) / max(1, len(teachers)), 2),
                }
            )
    return sorted(out, key=lambda b: -b["ratio"])


def isolated_students(db: DBSession) -> list[str]:
    adj = adjacency(db)
    incoming = {s: 0 for s in adj}
    for _, targets in adj.items():
        for t in targets:
            incoming[t] = incoming.get(t, 0) + 1
    return sorted(s for s in adj if not adj[s] and incoming.get(s, 0) == 0)


def teaching_load(db: DBSession) -> dict[str, int]:
    loads: dict[str, int] = {}
    for stat in db.query(EdgeStat).all():
        loads[stat.source_student] = loads.get(stat.source_student, 0) + stat.sessions
    return loads


def graph_health(db: DBSession) -> dict:
    current = edges(db)
    gaps = [c["transfer_gap"] for e in current for c in e["concepts"]]
    return {
        "student_count": db.query(Student).count(),
        "active_edge_count": len(current),
        "reciprocal_pair_count": len(reciprocal_pairs(db)),
        "cycle_count": len(find_cycles(db)),
        "isolated_student_count": len(isolated_students(db)),
        "bottleneck_concept_count": len(concept_bottlenecks(db)),
        "knowledge_hub_count": len(knowledge_hubs(db)),
        "average_transfer_gap": round(sum(gaps) / len(gaps), 4) if gaps else 0.0,
        "average_edge_score": round(sum(e["edge_score"] for e in current) / len(current), 4) if current else 0.0,
    }


def snapshot(db: DBSession) -> dict:
    return {
        "nodes": [{"id": s.id, "name": s.name} for s in db.query(Student).all()],
        "edges": edges(db),
        "reciprocal": reciprocal_pairs(db),
        "cycles": find_cycles(db),
        "hubs": knowledge_hubs(db),
        "bottlenecks": concept_bottlenecks(db),
        "isolated": isolated_students(db),
        "health": graph_health(db),
    }
