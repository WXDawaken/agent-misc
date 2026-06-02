"""Context routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..ir.common import (
    RequestEnvelope,
    ensure_supported_protocol,
    error_response,
    ok_response,
    require_session,
)
from ..ir.object_snapshot import ObjectSnapshot

router = APIRouter()


@router.post("/upsert")
def upsert_context(envelope: RequestEnvelope, request: Request):
    protocol_error = ensure_supported_protocol(envelope)
    if protocol_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(protocol_error))

    session_error = require_session(request.app.state.session_manager, envelope)
    if session_error is not None:
        return JSONResponse(status_code=404, content=jsonable_encoder(session_error))

    raw_snapshots = envelope.payload.get("snapshots")
    if not isinstance(raw_snapshots, list):
        invalid = error_response(
            envelope.request_id,
            code="INVALID_SNAPSHOT",
            message="Payload must include a list of snapshots.",
        )
        return JSONResponse(status_code=400, content=jsonable_encoder(invalid))

    snapshots = []
    try:
        for raw_snapshot in raw_snapshots:
            snapshots.append(ObjectSnapshot.model_validate(raw_snapshot))
    except ValidationError as exc:
        invalid = error_response(
            envelope.request_id,
            code="INVALID_SNAPSHOT",
            message="Snapshot validation failed.",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=400, content=jsonable_encoder(invalid))

    request.app.state.context_store.upsert_snapshots(envelope.session_id, snapshots)
    response = ok_response(
        envelope.request_id,
        {
            "snapshot_count": len(snapshots),
            "object_ids": [snapshot.object_id for snapshot in snapshots],
        },
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(response))
