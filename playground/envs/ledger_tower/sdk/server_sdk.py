from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from .result import StepResult
except ImportError:  # pragma: no cover - compatibility for direct module imports.
    from result import StepResult


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "ledger_tower" and ROOT.parent.name == "envs" else ROOT


def _resolve_workspace_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PLAYGROUND_ROOT / candidate


class LedgerTowerServerSDK:
    """HTTP client SDK for official server-backed Ledger Tower play.

    This module is intentionally server-only: importing it does not import
    ``game.py`` or require local game data in the agent workspace.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        game_id: str | None = None,
        new: bool = False,
        label: str | None = None,
        auth_token: str | None = None,
        token_role: str = "official",
    ) -> None:
        self.base_url = (base_url or os.environ.get("LEDGER_TOWER_SERVER_URL", "http://127.0.0.1:8765")).rstrip("/")
        self.token_role = token_role
        role_game_env = "LEDGER_TOWER_PRACTICE_GAME_ID" if token_role == "practice" else "LEDGER_TOWER_GAME_ID"
        role_token_env = "LEDGER_TOWER_PRACTICE_AUTH_TOKEN" if token_role == "practice" else "LEDGER_TOWER_AUTH_TOKEN"
        self.game_id = game_id or os.environ.get(role_game_env)
        self.auth_token = auth_token if auth_token is not None else os.environ.get(role_token_env)
        self.samples: list[dict[str, Any]] = []
        self.transcript: list[dict[str, Any]] = []
        if not new and not self.game_id:
            self.game_id = self._existing_token_game_id()
        if new or not self.game_id:
            payload: dict[str, Any] = {}
            if label:
                payload["label"] = label
            try:
                game_payload = self._request("POST", "/api/games", payload)
            except RuntimeError as exc:
                existing_game_id = self._existing_token_game_id() if "no remaining new games" in str(exc) else None
                if not existing_game_id:
                    raise
                self.game_id = existing_game_id
                self._sync(self._request("GET", f"/api/games/{urllib.parse.quote(self.game_id)}"))
            else:
                self.game_id = game_payload["summary"]["id"]
                self._sync(game_payload)
        else:
            self._sync(self._request("GET", f"/api/games/{urllib.parse.quote(self.game_id)}"))

    @classmethod
    def from_env(
        cls,
        *,
        game_id: str | None = None,
        new: bool = False,
        label: str | None = None,
        token_role: str = "official",
    ) -> "LedgerTowerServerSDK":
        return cls(game_id=game_id, new=new, label=label, token_role=token_role)

    def reset(self, *, label: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if label:
            payload["label"] = label
        game_payload = self._request("POST", "/api/games", payload)
        self.game_id = game_payload["summary"]["id"]
        self._sync(game_payload)
        return self.observe()

    def step(self, command: str) -> StepResult:
        game_id = self._quoted_game_id()
        game_payload = self._request("POST", f"/api/games/{game_id}/command", {"command": command})
        self._sync(game_payload)
        entry = game_payload["entry"]
        return StepResult(
            command=entry["command"],
            output=entry["output"],
            observation=game_payload["current"],
            reward=entry["reward"],
            done=bool(entry["done"]),
        )

    def run(self, commands: list[str]) -> list[StepResult]:
        results: list[StepResult] = []
        for command in commands:
            result = self.step(command)
            results.append(result)
            if result.done:
                break
        return results

    def run_script(self, script_path: str | Path) -> list[StepResult]:
        path = self._resolve_path(script_path)
        commands = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return self.run(commands)

    def observe(self, *, include_text: bool = True) -> dict[str, Any]:
        game_id = self._quoted_game_id()
        observation = self._request("GET", f"/api/games/{game_id}/state")
        if not include_text:
            observation = dict(observation)
            observation.pop("status_text", None)
        return observation

    def list_available(self, kind: str) -> str:
        game_id = self._quoted_game_id()
        encoded_kind = urllib.parse.quote(kind, safe="")
        payload = self._request("GET", f"/api/games/{game_id}/list/{encoded_kind}")
        return str(payload["output"])

    def score(self, goal: dict[str, Any] | None = None) -> dict[str, Any]:
        game_id = self._quoted_game_id()
        if goal is None:
            observation = self.observe(include_text=False)
            return observation["score"]
        return self._request("POST", f"/api/games/{game_id}/score", {"goal": goal})

    def verify(
        self,
        goal: dict[str, Any] | None = None,
        *,
        tick_budget: int | None = None,
        lifetime_tick_budget: int | None = None,
        soft_stop_tick: int | None = None,
        per_run_tick_budget: int | None = None,
    ) -> dict[str, Any]:
        game_id = self._quoted_game_id()
        payload: dict[str, Any] = {}
        if goal is not None:
            payload["goal"] = goal
        if tick_budget is not None:
            payload["tick_budget"] = tick_budget
        if lifetime_tick_budget is not None:
            payload["lifetime_tick_budget"] = lifetime_tick_budget
        if soft_stop_tick is not None:
            payload["soft_stop_tick"] = soft_stop_tick
        if per_run_tick_budget is not None:
            payload["per_run_tick_budget"] = per_run_tick_budget
        return self._request("POST", f"/api/games/{game_id}/verify", payload)

    def auth_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/auth/status")

    def trajectory(self) -> dict[str, Any]:
        game_id = self._quoted_game_id()
        return self._request("GET", f"/api/games/{game_id}/trajectory")

    def export_tracking(self, out_path: str | Path) -> Path:
        path = self._resolve_path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        trajectory = self.trajectory()
        payload = {
            "server": self.base_url,
            "game_id": self.game_id,
            "trajectory": trajectory,
            "samples": self.samples,
            "transcript": self.transcript,
            "final": self.observe(include_text=False),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def save(self, state_path: str | Path | None = None) -> str:
        if state_path is not None:
            raise ValueError("server-backed games are saved by the server")
        if not self.game_id:
            raise ValueError("no server game id")
        return self.game_id

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        return _resolve_workspace_path(path)

    def _quoted_game_id(self) -> str:
        if not self.game_id:
            raise ValueError("no server game id")
        return urllib.parse.quote(self.game_id, safe="")

    def _existing_token_game_id(self) -> str | None:
        if not self.auth_token:
            return None
        try:
            status = self._request("GET", "/api/auth/status")
        except RuntimeError:
            return None
        game_ids = status.get("game_ids") or []
        if len(game_ids) == 1:
            return str(game_ids[0])
        return None

    def _sync(self, game_payload: dict[str, Any]) -> None:
        summary = game_payload.get("summary") or {}
        if summary.get("id"):
            self.game_id = summary["id"]
        entries = game_payload.get("trajectory", {}).get("entries", [])
        self.transcript = [
            {
                "moves": entry.get("observation", {}).get("moves"),
                "command": entry.get("command"),
                "output": entry.get("output"),
            }
            for entry in entries
        ]
        self.samples = [
            {
                "index": entry.get("index"),
                "moves": entry.get("observation", {}).get("moves"),
                "command": entry.get("command"),
                "output": entry.get("output"),
                "metrics": entry.get("observation", {}).get("score", {}).get("metrics", {}),
            }
            for entry in entries
        ]

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = self.base_url + path
        body = None
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            headers["X-Ledger-Tower-Token"] = self.auth_token
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error_payload = json.loads(raw)
                message = error_payload.get("error", raw)
            except json.JSONDecodeError:
                message = raw or exc.reason
            raise RuntimeError(f"{method} {url} failed: {message}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc
        return json.loads(raw) if raw else {}


__all__ = ["LedgerTowerServerSDK"]
