"""Action routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..ir.common import (
    RequestEnvelope,
    ensure_supported_protocol,
    error_response,
    ok_response,
    require_session,
)

router = APIRouter()


def _reject_ambiguous_execution_request(envelope: RequestEnvelope):
    execution_intent = envelope.payload.get("execution_intent")
    clarification_needed = envelope.payload.get("requires_execution_clarification")
    ambiguous_intents = {"preview_or_execute", "unclear", "decide_later"}
    if execution_intent in ambiguous_intents or clarification_needed is True:
        clarification = error_response(
            envelope.request_id,
            code="REQUEST_CLARIFICATION_REQUIRED",
            message="Clarify whether this request is preview-only or should later route to plugin-local execution. Core will not guess.",
            details={
                "clarification_topic": "execution_mode",
                "execution_intent": execution_intent,
                "allowed_values": ["preview", "plugin_execute_after_preview"],
            },
        )
        return clarification
    return None


def _reject_core_execution_request(envelope: RequestEnvelope):
    execution_intent = envelope.payload.get("execution_intent")
    allow_core_execution = envelope.payload.get("allow_core_execution")
    forbidden_intents = {"apply", "apply_now", "execute", "mutate"}
    if execution_intent in forbidden_intents or allow_core_execution is True:
        violation = error_response(
            envelope.request_id,
            code="EXECUTION_BOUNDARY_VIOLATION",
            message="Core-side execution is forbidden. Keep execution local to the plugin and use preview-only requests here.",
            details={
                "execution_intent": execution_intent,
                "allow_core_execution": allow_core_execution,
            },
        )
        return violation
    return None


def _load_snapshot(request: Request, envelope: RequestEnvelope):
    object_id = envelope.payload.get("object_id")
    if not isinstance(object_id, str) or not object_id:
        invalid = error_response(
            envelope.request_id,
            code="INVALID_SNAPSHOT",
            message="Payload must include object_id.",
        )
        return None, invalid, 400

    snapshot = request.app.state.context_store.get_snapshot(envelope.session_id, object_id)
    if snapshot is None:
        missing = error_response(
            envelope.request_id,
            code="OBJECT_NOT_FOUND",
            message=f"Object '{object_id}' is not present in the session context.",
            details={"object_id": object_id},
        )
        return None, missing, 404
    return snapshot, None, 200


@router.post("/suggest")
def suggest_actions(envelope: RequestEnvelope, request: Request):
    protocol_error = ensure_supported_protocol(envelope)
    if protocol_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(protocol_error))

    clarification_error = _reject_ambiguous_execution_request(envelope)
    if clarification_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(clarification_error))

    boundary_error = _reject_core_execution_request(envelope)
    if boundary_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(boundary_error))

    session_error = require_session(request.app.state.session_manager, envelope)
    if session_error is not None:
        return JSONResponse(status_code=404, content=jsonable_encoder(session_error))

    snapshot, error, status_code = _load_snapshot(request, envelope)
    if error is not None:
        return JSONResponse(status_code=status_code, content=jsonable_encoder(error))

    actions = request.app.state.planner.suggest(snapshot)
    response = ok_response(
        envelope.request_id,
        {"actions": [action.model_dump(mode="json") for action in actions]},
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(response))


@router.post("/explain")
def explain_action(envelope: RequestEnvelope, request: Request):
    protocol_error = ensure_supported_protocol(envelope)
    if protocol_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(protocol_error))

    clarification_error = _reject_ambiguous_execution_request(envelope)
    if clarification_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(clarification_error))

    boundary_error = _reject_core_execution_request(envelope)
    if boundary_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(boundary_error))

    session_error = require_session(request.app.state.session_manager, envelope)
    if session_error is not None:
        return JSONResponse(status_code=404, content=jsonable_encoder(session_error))

    snapshot, error, status_code = _load_snapshot(request, envelope)
    if error is not None:
        return JSONResponse(status_code=status_code, content=jsonable_encoder(error))

    action_id = envelope.payload.get("action_id")
    explanation = request.app.state.planner.explain(snapshot, action_id)
    if explanation is None:
        unknown = error_response(
            envelope.request_id,
            code="UNKNOWN_ACTION",
            message=f"Unknown action '{action_id}'.",
            details={"action_id": action_id},
        )
        return JSONResponse(status_code=404, content=jsonable_encoder(unknown))

    response = ok_response(envelope.request_id, explanation)
    return JSONResponse(status_code=200, content=jsonable_encoder(response))


@router.post("/plan")
def plan_action(envelope: RequestEnvelope, request: Request):
    protocol_error = ensure_supported_protocol(envelope)
    if protocol_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(protocol_error))

    clarification_error = _reject_ambiguous_execution_request(envelope)
    if clarification_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(clarification_error))

    boundary_error = _reject_core_execution_request(envelope)
    if boundary_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(boundary_error))

    session_error = require_session(request.app.state.session_manager, envelope)
    if session_error is not None:
        return JSONResponse(status_code=404, content=jsonable_encoder(session_error))

    snapshot, error, status_code = _load_snapshot(request, envelope)
    if error is not None:
        return JSONResponse(status_code=status_code, content=jsonable_encoder(error))

    action_id = envelope.payload.get("action_id")
    plan = request.app.state.planner.plan(snapshot, action_id)
    if plan is None:
        unknown = error_response(
            envelope.request_id,
            code="UNKNOWN_ACTION",
            message=f"Unknown action '{action_id}'.",
            details={"action_id": action_id},
        )
        return JSONResponse(status_code=404, content=jsonable_encoder(unknown))

    response = ok_response(envelope.request_id, {"plan": plan.model_dump(mode="json")})
    return JSONResponse(status_code=200, content=jsonable_encoder(response))


@router.post("/patch")
def patch_action(envelope: RequestEnvelope, request: Request):
    protocol_error = ensure_supported_protocol(envelope)
    if protocol_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(protocol_error))

    clarification_error = _reject_ambiguous_execution_request(envelope)
    if clarification_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(clarification_error))

    boundary_error = _reject_core_execution_request(envelope)
    if boundary_error is not None:
        return JSONResponse(status_code=400, content=jsonable_encoder(boundary_error))

    session_error = require_session(request.app.state.session_manager, envelope)
    if session_error is not None:
        return JSONResponse(status_code=404, content=jsonable_encoder(session_error))

    snapshot, error, status_code = _load_snapshot(request, envelope)
    if error is not None:
        return JSONResponse(status_code=status_code, content=jsonable_encoder(error))

    action_id = envelope.payload.get("action_id")
    patch = request.app.state.planner.patch(snapshot, action_id)
    if patch is None:
        unknown = error_response(
            envelope.request_id,
            code="UNKNOWN_ACTION",
            message=f"Unknown action '{action_id}'.",
            details={"action_id": action_id},
        )
        return JSONResponse(status_code=404, content=jsonable_encoder(unknown))

    response = ok_response(envelope.request_id, {"patch": patch.model_dump(mode="json")})
    return JSONResponse(status_code=200, content=jsonable_encoder(response))
