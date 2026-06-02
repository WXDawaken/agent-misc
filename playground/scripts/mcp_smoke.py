from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def encode(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def read_message(proc: subprocess.Popen[bytes]) -> dict[str, Any]:
    headers: dict[str, str] = {}
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed stdout")
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(proc.stdout.read(length).decode("utf-8"))


def request(proc: subprocess.Popen[bytes], idx: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    proc.stdin.write(encode({"jsonrpc": "2.0", "id": idx, "method": method, "params": params or {}}))
    proc.stdin.flush()
    return read_message(proc)


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "mcp_server.py")],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin and proc.stdout
    try:
        print(request(proc, 1, "initialize", {"protocolVersion": "2024-11-05"})["result"]["serverInfo"])
        print(request(proc, 2, "tools/list")["result"]["tools"][0]["name"])
        result = request(proc, 3, "tools/call", {
            "name": "run_commands",
            "arguments": {"commands": ["study ember 2", "study stone 2", "status"]},
        })
        print(result["result"]["content"][0]["text"][:500])
        resources = request(proc, 4, "resources/list")["result"]["resources"]
        print([r["uri"] for r in resources])
    finally:
        proc.kill()
        proc.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
