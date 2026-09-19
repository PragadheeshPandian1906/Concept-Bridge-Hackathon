from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slice.config import get_settings

from ..persistence.database import init_db
from .routes import core, graph, matching, runs, sessions

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="ConceptBridge API",
    version="1.0.0",
    description="From Concept Gaps to Complementary Connections - agentic peer-learning backend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(core.router, prefix=PREFIX)
app.include_router(graph.router, prefix=PREFIX)
app.include_router(matching.router, prefix=PREFIX)
app.include_router(sessions.router, prefix=PREFIX)
app.include_router(runs.router, prefix=PREFIX)


@app.get(f"{PREFIX}/health", tags=["health"])
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "model": settings.model if not settings.demo_mode else None,
    }
