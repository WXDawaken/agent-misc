"""Protocol envelope helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "0.1"


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RequestEnvelope(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    request_id: str
    session_id: str | None = None
    project_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ResponseEnvelope(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    request_id: str
    ok: bool
    error: ErrorInfo | None = None
    data: dict[str, Any] | None = None


def ok_response(request_id: str, data: dict[str, Any]) -> ResponseEnvelope:
    return ResponseEnvelope(request_id=request_id, ok=True, data=data)


def error_response(
    request_id: str,
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ResponseEnvelope:
    return ResponseEnvelope(
        request_id=request_id,
        ok=False,
        error=ErrorInfo(code=code, message=message, details=details or {}),
        data=None,
    )


def ensure_supported_protocol(envelope: RequestEnvelope) -> ResponseEnvelope | None:
    if envelope.protocol_version != PROTOCOL_VERSION:
        return error_response(
            envelope.request_id,
            code="UNSUPPORTED_PROTOCOL_VERSION",
            message=f"Unsupported protocol version '{envelope.protocol_version}'.",
            details={"expected": PROTOCOL_VERSION},
        )
    return None


def require_session(session_manager, envelope: RequestEnvelope) -> ResponseEnvelope | None:
    if session_manager.has_session(envelope.session_id):
        return None
    return error_response(
        envelope.request_id,
        code="SESSION_NOT_FOUND",
        message=f"Session '{envelope.session_id}' was not found.",
        details={"session_id": envelope.session_id},
    )
