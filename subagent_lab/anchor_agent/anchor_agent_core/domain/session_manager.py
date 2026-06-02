"""In-memory session lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    project_id: str


class InMemorySessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def open_session(self, project_id: str, requested_session_id: str | None = None) -> SessionRecord:
        session_id = requested_session_id or f"sess_{uuid.uuid4().hex[:12]}"
        session = SessionRecord(session_id=session_id, project_id=project_id)
        self._sessions[session_id] = session
        return session

    def has_session(self, session_id: str | None) -> bool:
        return bool(session_id) and session_id in self._sessions
