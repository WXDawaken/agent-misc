from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


MAX_FIELD_CHARS = 2000

DENY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "process_termination",
        re.compile(
            r"\b(taskkill|stop-process|killall|pkill)\b|"
            r"\bwmic\s+process\b.*\b(call\s+terminate|delete)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "background_process",
        re.compile(
            r"\b(start-process|start-job|nohup|setsid|pythonw)\b|"
            r"\bcmd(?:\.exe)?\s*/c\s+start\b|"
            r"\bpowershell(?:\.exe)?\b.*\b-windowstyle\s+hidden\b",
            re.IGNORECASE,
        ),
    ),
    (
        "recursive_destructive_delete",
        re.compile(
            r"\bremove-item\b(?=.*\b-recurse\b)(?=.*\b-force\b)|"
            r"\brm\b\s+-[^\n\r]*r[^\n\r]*f|"
            r"\brm\b\s+-[^\n\r]*f[^\n\r]*r|"
            r"\brmdir\b\s+/s\b|"
            r"\bdel\b\s+/s\b",
            re.IGNORECASE,
        ),
    ),
)


def _compact(value: Any, limit: int = MAX_FIELD_CHARS) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = repr(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...<truncated {len(text) - limit} chars>"


def _tool_command(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
        return _compact(tool_input)
    if isinstance(tool_input, str):
        return tool_input
    return _compact(tool_input)


def _append_log(payload: dict[str, Any], command: str, decision: dict[str, str] | None) -> None:
    log_path = os.environ.get("PLAYGROUND_CODEX_HOOK_LOG")
    if not log_path:
        return
    try:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "hook_event_name": payload.get("hook_event_name"),
            "permission_mode": payload.get("permission_mode"),
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "tool_name": payload.get("tool_name"),
            "tool_use_id": payload.get("tool_use_id"),
            "cwd": payload.get("cwd"),
            "model": payload.get("model"),
            "command": _compact(command),
            "decision": decision,
        }
        if payload.get("hook_event_name") == "PostToolUse":
            record["tool_response"] = _compact(payload.get("tool_response"))
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        # Hooks must not fail closed just because audit logging failed.
        return


def _deny_reason(command: str) -> dict[str, str] | None:
    for rule_name, pattern in DENY_RULES:
        if pattern.search(command):
            return {
                "rule": rule_name,
                "reason": (
                    f"Blocked by playground Codex tool policy ({rule_name}). "
                    "Use bounded foreground helper scripts and avoid process management or destructive cleanup."
                ),
            }
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0

    event_name = str(payload.get("hook_event_name") or "")
    command = _tool_command(payload)
    decision = _deny_reason(command) if event_name == "PreToolUse" else None
    _append_log(payload, command, decision)

    if decision:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": decision["reason"],
                    }
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
