"""Session routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..ir.common import RequestEnvelope, ensure_supported_protocol, ok_response

router = APIRouter()


@router.post("/open")
def open_session(envelope: RequestEnvelope, request: Request):
    protocol_error = ensure_supported_protocol(envelope)
    if protocol_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(protocol_error))

    session = request.app.state.session_manager.open_session(
        project_id=envelope.project_id,
        requested_session_id=envelope.session_id,
    )
    response = ok_response(
        envelope.request_id,
        {
            "session_id": session.session_id,
            "project_id": session.project_id,
        },
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(response))
