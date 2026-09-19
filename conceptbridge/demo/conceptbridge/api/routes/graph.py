from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from ...matchmaking import graph as G
from ...persistence.database import get_db

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def current_graph(db: DBSession = Depends(get_db)):
    return G.snapshot(db)


@router.post("/rebuild")
def rebuild(db: DBSession = Depends(get_db)):
    return G.build_graph(db)


@router.get("/edges")
def edges(db: DBSession = Depends(get_db)):
    return G.edges(db)


@router.get("/students/{student_id}")
def student_edges(student_id: str, db: DBSession = Depends(get_db)):
    all_edges = G.edges(db)
    return {
        "student_id": student_id,
        "outgoing": [e for e in all_edges if e["source"] == student_id],
        "incoming": [e for e in all_edges if e["target"] == student_id],
    }


@router.get("/cycles")
def cycles(db: DBSession = Depends(get_db)):
    return G.find_cycles(db)


@router.get("/reciprocal")
def reciprocal(db: DBSession = Depends(get_db)):
    return G.reciprocal_pairs(db)


@router.get("/hubs")
def hubs(db: DBSession = Depends(get_db)):
    return G.knowledge_hubs(db)


@router.get("/bottlenecks")
def bottlenecks(db: DBSession = Depends(get_db)):
    return G.concept_bottlenecks(db)


@router.get("/isolated")
def isolated(db: DBSession = Depends(get_db)):
    return G.isolated_students(db)


@router.get("/health")
def health(db: DBSession = Depends(get_db)):
    return G.graph_health(db)
