"""In-memory snapshot storage."""

from __future__ import annotations

from ..ir.object_snapshot import ObjectSnapshot


class InMemoryContextStore:
    def __init__(self) -> None:
        self._snapshots_by_session: dict[str, dict[str, ObjectSnapshot]] = {}

    def upsert_snapshots(self, session_id: str, snapshots: list[ObjectSnapshot]) -> None:
        session_snapshots = self._snapshots_by_session.setdefault(session_id, {})
        for snapshot in snapshots:
            session_snapshots[snapshot.object_id] = snapshot

    def get_snapshot(self, session_id: str, object_id: str) -> ObjectSnapshot | None:
        return self._snapshots_by_session.get(session_id, {}).get(object_id)
