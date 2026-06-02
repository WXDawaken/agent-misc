from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "ledger_tower" and ROOT.parent.name == "envs" else ROOT
if str(PLAYGROUND_ROOT) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from envs.ledger_tower.sdk import LedgerTowerSDK
except ImportError:  # pragma: no cover - flattened workspace compatibility.
    from sdk import LedgerTowerSDK  # type: ignore[no-redef]


SERVER_NAME = "ledger-tower"
SERVER_VERSION = "0.1.0"

sdk = LedgerTowerSDK(new=True, autosave=False)


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    raw = sys.stdin.buffer.read(length)
    return json.loads(raw.decode("utf-8"))


def write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def text_content(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, str):
        value = json.dumps(value, indent=2, sort_keys=True)
    return [{"type": "text", "text": value}]


def tool_schema() -> list[dict[str, Any]]:
    return [
        {
            "name": "new_game",
            "description": "Reset Ledger Tower to a fresh deterministic game state.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "save": {"type": "boolean", "description": "Write the reset state to the current save path."}
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "observe",
            "description": "Return the current structured game state and status text.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "execute_command",
            "description": "Execute one Ledger Tower command such as 'move east' or 'preview north'.",
            "inputSchema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
        {
            "name": "run_commands",
            "description": "Execute a short list of Ledger Tower commands in order.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 80,
                    }
                },
                "required": ["commands"],
                "additionalProperties": False,
            },
        },
        {
            "name": "list_available",
            "description": "List commands, enemies, items, shops, floors, goals, entities, or reference rules.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["commands", "enemies", "items", "shops", "floors", "goals", "entities", "reference"],
                    }
                },
                "required": ["kind"],
                "additionalProperties": False,
            },
        },
        {
            "name": "score",
            "description": "Return verifier-style reward metrics, optionally with a target goal.",
            "inputSchema": {
                "type": "object",
                "properties": {"goal": {"type": "object"}},
                "additionalProperties": False,
            },
        },
        {
            "name": "save_game",
            "description": "Save the current game state to a JSON file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "state_path": {"type": "string", "description": "Optional save path relative to playground."}
                },
                "additionalProperties": False,
            },
        },
    ]


def resource_defs() -> list[dict[str, str]]:
    return [
        {
            "uri": "ledger-tower://agent-brief",
            "name": "Agent Brief",
            "description": "Short play instructions and command list.",
            "mimeType": "text/markdown",
        },
        {
            "uri": "ledger-tower://design",
            "name": "Design Notes",
            "description": "Design scope, capability axis, and scoring notes.",
            "mimeType": "text/markdown",
        },
        {
            "uri": "ledger-tower://sdk-api",
            "name": "SDK API",
            "description": "Programmatic SDK and MCP usage notes.",
            "mimeType": "text/markdown",
        },
    ]


def read_resource(uri: str) -> str:
    mapping = {
        "ledger-tower://agent-brief": ROOT / "docs" / "agent-brief.md",
        "ledger-tower://design": ROOT / "docs" / "design.md",
        "ledger-tower://sdk-api": ROOT / "docs" / "sdk-api.md",
    }
    if uri not in mapping:
        raise ValueError(f"Unknown resource: {uri}")
    return mapping[uri].read_text(encoding="utf-8")


def call_tool(name: str, args: dict[str, Any]) -> Any:
    if name == "new_game":
        return sdk.reset(save=bool(args.get("save", False)))
    if name == "observe":
        return sdk.observe()
    if name == "execute_command":
        return sdk.step(str(args["command"])).to_dict()
    if name == "run_commands":
        return [result.to_dict() for result in sdk.run([str(command) for command in args["commands"]])]
    if name == "list_available":
        return sdk.list_available(str(args["kind"]))
    if name == "score":
        return sdk.score(args.get("goal"))
    if name == "save_game":
        return {"saved_to": str(sdk.save(args.get("state_path")))}
    raise ValueError(f"Unknown tool: {name}")


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}
    if request_id is None:
        return None

    if method == "initialize":
        requested = params.get("protocolVersion") or "2024-11-05"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": requested,
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tool_schema()}}
    if method == "tools/call":
        result = call_tool(params["name"], params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": text_content(result)}}
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": resource_defs()}}
    if method == "resources/read":
        uri = params["uri"]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "contents": [{
                    "uri": uri,
                    "mimeType": "text/markdown",
                    "text": read_resource(uri),
                }]
            },
        }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    while True:
        request = read_message()
        if request is None:
            break
        try:
            response = handle(request)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32000, "message": str(exc)},
            }
        if response is not None:
            write_message(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
