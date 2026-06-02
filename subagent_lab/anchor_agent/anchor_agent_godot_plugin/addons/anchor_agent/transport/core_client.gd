@tool
extends RefCounted

const DEFAULT_BASE_URL := "http://127.0.0.1:37901"
const PROTOCOL_VERSION := "0.1"


func build_envelope(request_id: String, session_id: String, project_id: String, payload: Dictionary) -> Dictionary:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "session_id": session_id,
        "project_id": project_id,
        "payload": payload
    }


func build_request_path(route: String) -> String:
    return "%s%s" % [DEFAULT_BASE_URL, route]
