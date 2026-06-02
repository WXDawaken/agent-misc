@tool
extends RefCounted

const PROTOCOL_VERSION := "0.1"


static func request_envelope(request_id: String, session_id: String, project_id: String, payload: Dictionary) -> Dictionary:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "session_id": session_id,
        "project_id": project_id,
        "payload": payload
    }
