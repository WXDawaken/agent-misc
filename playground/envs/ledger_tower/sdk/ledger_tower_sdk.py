from __future__ import annotations

import json
import os
import sys
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from .. import game  # type: ignore[import-not-found]  # noqa: E402
except ImportError:  # pragma: no cover - flattened agent workspace compatibility.
    import game  # type: ignore[no-redef]  # noqa: E402


DEFAULT_STATE = PLAYGROUND_ROOT / "saves" / "ledger_tower_sdk_state.json"


def _resolve_workspace_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PLAYGROUND_ROOT / candidate


def _resolve_script_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    environment_candidate = ROOT / candidate
    if environment_candidate.exists():
        return environment_candidate
    return PLAYGROUND_ROOT / candidate


class LedgerTowerSDK:
    """Direct local SDK for deterministic Ledger Tower practice."""

    def __init__(
        self,
        state_path: str | Path | None = None,
        *,
        new: bool = False,
        autosave: bool = False,
        seed: str | None = None,
        budget: dict[str, Any] | None = None,
        data_path: str | Path | None = None,
    ) -> None:
        self.state_path = self._resolve_path(state_path) if state_path else DEFAULT_STATE
        persisted_data_path = None if new else self._state_data_path(self.state_path)
        self.data_path = game.resolve_data_path(data_path or persisted_data_path)
        self.data = game.load_data(self.data_path)
        self.autosave = autosave
        self.samples: list[dict[str, Any]] = []
        self.transcript: list[dict[str, Any]] = []
        if new:
            self.state = game.fresh_state(self.data, seed=seed, budget=budget, data_path=self.data_path)
        else:
            self.state = game.load_state(self.state_path, self.data, force_new=False)
            if budget:
                self.state["budget"] = dict(budget)
        self._sample("init", "session started")

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        return _resolve_workspace_path(path)

    @staticmethod
    def _state_data_path(path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        raw = payload.get("data_path")
        return str(raw) if raw else None

    def reset(
        self,
        *,
        save: bool | None = None,
        seed: str | None = None,
        budget: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.state = game.fresh_state(self.data, seed=seed, budget=budget, data_path=self.data_path)
        self.samples = []
        self.transcript = []
        self._sample("reset", "new game")
        should_save = save if save is not None else self.autosave
        if should_save:
            self.save()
        return self.observe()

    def save(self, state_path: str | Path | None = None) -> Path:
        if state_path:
            self.state_path = self._resolve_path(state_path)
        game.save_state(self.state_path, self.state)
        return self.state_path

    def step(self, command: str) -> StepResult:
        keep_going, output = game.execute(command, self.state, self.data)
        if command.strip().lower() == "save":
            self.save()
        if self.autosave and keep_going:
            self.save()
        self.transcript.append({
            "moves": self.state["moves"],
            "command": command,
            "output": output,
        })
        self._sample(command, output)
        return StepResult(
            command=command,
            output=output,
            observation=self.observe(include_text=False),
            reward=self.score()["reward"],
            done=not keep_going or bool(self.state.get("done")),
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
        path = _resolve_script_path(script_path)
        commands = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return self.run(commands)

    def observe(self, *, include_text: bool = True) -> dict[str, Any]:
        return game.observe_state(self.state, self.data, include_text=include_text)

    def list_available(self, kind: str) -> str:
        return game.cmd_list(kind, self.state, self.data)

    def score(self, goal: dict[str, Any] | None = None) -> dict[str, Any]:
        return game.score(self.state, self.data, goal)

    def metrics(self) -> dict[str, Any]:
        return game.metrics(self.state, self.data)

    def export_tracking(self, out_path: str | Path) -> Path:
        path = self._resolve_path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "game": self.data["metadata"],
            "state_path": str(self.state_path),
            "samples": self.samples,
            "transcript": self.transcript,
            "final": self.observe(include_text=False),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _sample(self, command: str, output: str) -> None:
        self.samples.append({
            "index": len(self.samples),
            "moves": self.state["moves"],
            "command": command,
            "output": output,
            "metrics": self.metrics(),
        })


class LedgerTowerServerSDK:
    """HTTP client SDK for official server-backed Ledger Tower play."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        game_id: str | None = None,
        new: bool = False,
        label: str | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("LEDGER_TOWER_SERVER_URL", "http://127.0.0.1:8765")).rstrip("/")
        self.game_id = game_id or os.environ.get("LEDGER_TOWER_GAME_ID")
        self.auth_token = auth_token if auth_token is not None else os.environ.get("LEDGER_TOWER_AUTH_TOKEN")
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
    ) -> "LedgerTowerServerSDK":
        return cls(game_id=game_id, new=new, label=label)

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
