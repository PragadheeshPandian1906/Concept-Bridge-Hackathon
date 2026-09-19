from demo.conceptbridge.config import get_config
from demo.conceptbridge.matchmaking import graph as G
from demo.conceptbridge.orchestrator import run_profiling


def build(seeded):
    db, run_id = seeded
    run_profiling(db, run_id)
    G.build_graph(db)
    return db


def test_edges_respect_thresholds(seeded):
    db = build(seeded)
    cfg = get_config()
    for edge in G.edges(db):
        for concept in edge["concepts"]:
            assert concept["teacher_score"] >= cfg.strength_threshold
            assert concept["learner_score"] < cfg.gap_threshold
            assert concept["transfer_gap"] >= cfg.min_transfer_gap


def test_no_self_edges(seeded):
    db = build(seeded)
    assert all(e["source"] != e["target"] for e in G.edges(db))


def test_reciprocal_and_cycles(seeded):
    db = build(seeded)
    pairs = [tuple(p["students"]) for p in G.reciprocal_pairs(db)]
    assert ("S001", "S002") in pairs
    cycles = G.find_cycles(db)
    assert any(len(c) == 3 for c in cycles)


def test_hubs_bottlenecks_isolated(seeded):
    db = build(seeded)
    assert G.knowledge_hubs(db)
    assert any(b["concept_id"] == "C_SQL" for b in G.concept_bottlenecks(db))
    assert G.isolated_students(db) == ["S008"]


def test_graph_health_shape(seeded):
    db = build(seeded)
    health = G.graph_health(db)
    assert health["student_count"] == 8
    assert health["active_edge_count"] > 0
