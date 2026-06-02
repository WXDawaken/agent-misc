"""FastAPI server assembly for Anchor Agent core."""

from __future__ import annotations

from fastapi import FastAPI

from ..api.routes_actions import router as actions_router
from ..api.routes_context import router as context_router
from ..api.routes_session import router as session_router
from ..domain.context_store import InMemoryContextStore
from ..domain.planner import RuleBasedPlanner
from ..domain.session_manager import InMemorySessionManager


def create_app() -> FastAPI:
    app = FastAPI(
        title="Anchor Agent Core",
        version="0.1",
        description="Selection-driven object helper for Godot editor experiments.",
    )
    app.state.session_manager = InMemorySessionManager()
    app.state.context_store = InMemoryContextStore()
    app.state.planner = RuleBasedPlanner()
    app.include_router(session_router, prefix="/v1/session", tags=["session"])
    app.include_router(context_router, prefix="/v1/context", tags=["context"])
    app.include_router(actions_router, prefix="/v1/actions", tags=["actions"])
    return app
