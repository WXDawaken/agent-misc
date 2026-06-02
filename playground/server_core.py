from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import threading
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Protocol


class AuthError(ValueError):
    pass


GAME_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SOFT_STOP_SCORING_BINARY = "binary"
SOFT_STOP_SCORING_LINEAR_TO_HARD_BUDGET = "linear_to_hard_budget"
SOFT_STOP_SCORING_CHOICES = {
    SOFT_STOP_SCORING_BINARY,
    SOFT_STOP_SCORING_LINEAR_TO_HARD_BUDGET,
}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_game_id(game_id: str) -> str:
    if not GAME_ID_RE.match(game_id):
        raise ValueError("invalid game id")
    return game_id


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_soft_stop_scoring(value: Any | None) -> str:
    if value is None or value == "":
        return SOFT_STOP_SCORING_BINARY
    normalized = str(value).strip().lower().replace("-", "_")
    aliases = {
        "legacy": SOFT_STOP_SCORING_BINARY,
        "hard": SOFT_STOP_SCORING_BINARY,
        "linear": SOFT_STOP_SCORING_LINEAR_TO_HARD_BUDGET,
        "linear_to_hard": SOFT_STOP_SCORING_LINEAR_TO_HARD_BUDGET,
        "linear_to_budget": SOFT_STOP_SCORING_LINEAR_TO_HARD_BUDGET,
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SOFT_STOP_SCORING_CHOICES:
        known = ", ".join(sorted(SOFT_STOP_SCORING_CHOICES))
        raise ValueError(f"unknown soft stop scoring policy {value!r}; known policies: {known}")
    return normalized


def soft_stop_score(
    *,
    scoring: str | None,
    used: int,
    soft_stop: int | None,
    hard_limit: int | None,
) -> int | float | None:
    if soft_stop is None:
        return None
    policy = normalize_soft_stop_scoring(scoring)
    overrun = max(0, int(used) - int(soft_stop))
    if policy == SOFT_STOP_SCORING_BINARY:
        return int(overrun == 0)
    window = max(1, int(hard_limit) - int(soft_stop)) if hard_limit is not None else 1
    return round(max(0.0, min(1.0, 1.0 - (overrun / window))), 4)


def trajectory_hash(trajectory: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "session": trajectory.get("session", {}),
            "entries": trajectory.get("entries", []),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _goal_status_achieved(status: Any) -> bool:
    if isinstance(status, bool):
        return status
    if isinstance(status, dict) and "achieved" in status:
        return bool(status["achieved"])
    return bool(status)


def score_goal_completion(score: dict[str, Any]) -> dict[str, Any]:
    existing = score.get("goal_completion")
    if isinstance(existing, dict):
        failed = list(existing.get("failed", []))
        total = int(existing.get("total", 0) or 0)
        achieved_count = int(existing.get("achieved_count", total - len(failed)) or 0)
        achieved = existing.get("achieved")
    else:
        goal_status = score.get("goal", {})
        failed = [
            name
            for name, status in goal_status.items()
            if not _goal_status_achieved(status)
        ]
        total = len(goal_status)
        achieved_count = total - len(failed)
        achieved = None if total == 0 else not failed
    return {
        "achieved": achieved,
        "achievedCount": achieved_count,
        "total": total,
        "failed": failed,
    }


def verification_outcome(*, accepted: bool, goal_achieved: bool | None) -> str:
    if not accepted:
        return "rejected"
    if goal_achieved is False:
        return "partial"
    if goal_achieved is True:
        return "success"
    return "accepted"


@dataclass(frozen=True)
class StepOutcome:
    output: str
    reward: int
    done: bool


class EnvironmentAdapter(Protocol):
    env_id: str
    display_name: str

    def new_session(
        self,
        state_path: Path,
        *,
        token_info: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> Any: ...
    def load_session(self, state_path: Path) -> Any: ...
    def save_session(self, session: Any) -> None: ...
    def observe(self, session: Any, *, include_text: bool = True) -> dict[str, Any]: ...
    def step(self, session: Any, command: str) -> StepOutcome: ...
    def list_available(self, session: Any, kind: str) -> str: ...
    def score(self, session: Any, goal: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def metrics(self, session: Any) -> dict[str, Any]: ...
    def session_metadata(self, session: Any) -> dict[str, Any]: ...
    def summary_fields(self, observation: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]: ...
    def trajectory_metrics(self, trajectory: dict[str, Any]) -> dict[str, Any]: ...
    def budget_policy(self) -> dict[str, Any]: ...


class GameStoreProtocol(Protocol):
    games_root: Path

    def new_game_id(self) -> str: ...
    def list_games(self) -> list[dict[str, Any]]: ...
    def get_game(self, game_id: str) -> dict[str, Any]: ...
    def list_available(self, game_id: str, kind: str) -> str: ...
    def create_game(
        self,
        label: str | None = None,
        *,
        token_info: dict[str, Any] | None = None,
        game_id: str | None = None,
        **options: Any,
    ) -> dict[str, Any]: ...
    def step_game(self, game_id: str, command: str) -> dict[str, Any]: ...
    def run_commands(self, game_id: str, commands: list[str]) -> dict[str, Any]: ...
    def score_game(self, game_id: str, goal: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def verify_game(
        self,
        game_id: str,
        *,
        token_info: dict[str, Any],
        goal: dict[str, Any] | None = None,
        tick_budget: int | None = None,
        lifetime_tick_budget: int | None = None,
        soft_stop_tick: int | None = None,
        per_run_tick_budget: int | None = None,
    ) -> dict[str, Any]: ...


class TokenRegistryProtocol(Protocol):
    path: Path

    def status(self, token: str) -> dict[str, Any]: ...
    def consume_new_game(self, token: str, game_id: str) -> dict[str, Any]: ...
    def require_game(self, token: str, game_id: str) -> dict[str, Any]: ...
    def mark_verified(self, token: str, game_id: str) -> dict[str, Any]: ...


class TokenRegistryBase:
    def __init__(self, path: Path, *, env_id: str) -> None:
        self.path = path
        self.env_id = env_id
        self._lock = threading.RLock()

    def mint(
        self,
        *,
        task_id: str,
        env_id: str | None = None,
        track: str | None = None,
        max_new_games: int = 1,
        ttl_seconds: int = 3600,
        goal: dict[str, Any] | None = None,
        tick_budget: int | None = None,
        soft_stop_tick: int | None = None,
        soft_stop_scoring: str | None = None,
        per_run_tick_budget: int | None = None,
        token_role: str = "official",
        official: bool = True,
        scoring: str | None = None,
        extra_record: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if max_new_games < 1:
            raise ValueError("max_new_games must be at least 1")
        resolved_env_id = env_id or self.env_id
        raw_token = secrets.token_urlsafe(32)
        digest = token_hash(raw_token)
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=ttl_seconds)
        record = {
            "token_hash": digest,
            "task_id": task_id,
            "env_id": resolved_env_id,
            "track": track,
            "created_at": created_at.isoformat(timespec="seconds"),
            "expires_at": expires_at.isoformat(timespec="seconds"),
            "max_new_games": int(max_new_games),
            "used_new_games": 0,
            "game_ids": [],
            "verified_game_ids": [],
            "revoked": False,
            "goal": goal or None,
            "tick_budget": tick_budget,
            "soft_stop_tick": soft_stop_tick,
            "soft_stop_scoring": normalize_soft_stop_scoring(soft_stop_scoring),
            "per_run_tick_budget": per_run_tick_budget,
            "token_role": token_role,
            "official": bool(official),
            "scoring": scoring,
        }
        if extra_record:
            record.update(extra_record)
        with self._lock:
            registry = self._load()
            registry["tokens"][digest] = record
            self._save(registry)
        public = {
            "token": raw_token,
            "token_hash": digest,
            "task_id": task_id,
            "env_id": resolved_env_id,
            "track": track,
            "expires_at": expires_at.isoformat(timespec="seconds"),
            "max_new_games": int(max_new_games),
            "goal": goal or None,
            "tick_budget": tick_budget,
            "tick_budget_type": "lifetime",
            "soft_stop_tick": soft_stop_tick,
            "soft_stop_scoring": record["soft_stop_scoring"],
            "per_run_tick_budget": per_run_tick_budget,
            "token_role": token_role,
            "official": bool(official),
            "scoring": scoring,
        }
        public.update(self._public_policy(record))
        return public

    def status(self, token: str) -> dict[str, Any]:
        digest, record = self._require_record(token)
        public = self._public_record(record)
        public["token_hash"] = digest
        return public

    def consume_new_game(self, token: str, game_id: str) -> dict[str, Any]:
        digest = token_hash(token)
        with self._lock:
            registry = self._load()
            record = self._validate_record(registry, digest)
            if int(record.get("used_new_games", 0)) >= int(record.get("max_new_games", 0)):
                raise AuthError("token has no remaining new games")
            record["used_new_games"] = int(record.get("used_new_games", 0)) + 1
            game_ids = record.setdefault("game_ids", [])
            if game_id not in game_ids:
                game_ids.append(game_id)
            registry["tokens"][digest] = record
            self._save(registry)
        public = self._public_record(record)
        public["token_hash"] = digest
        public.update(self._game_private_policy(record))
        return public

    def require_game(self, token: str, game_id: str) -> dict[str, Any]:
        digest, record = self._require_record(token)
        if game_id not in record.get("game_ids", []):
            raise AuthError("token does not own this game")
        public = self._public_record(record)
        public["token_hash"] = digest
        return public

    def mark_verified(self, token: str, game_id: str) -> dict[str, Any]:
        digest = token_hash(token)
        with self._lock:
            registry = self._load()
            record = self._validate_record(registry, digest)
            if game_id not in record.get("game_ids", []):
                raise AuthError("token does not own this game")
            verified = record.setdefault("verified_game_ids", [])
            if game_id not in verified:
                verified.append(game_id)
            registry["tokens"][digest] = record
            self._save(registry)
        public = self._public_record(record)
        public["token_hash"] = digest
        return public

    def _require_record(self, token: str) -> tuple[str, dict[str, Any]]:
        digest = token_hash(token)
        with self._lock:
            registry = self._load()
            record = self._validate_record(registry, digest)
        return digest, record

    def _validate_record(self, registry: dict[str, Any], digest: str) -> dict[str, Any]:
        record = registry.get("tokens", {}).get(digest)
        if not record:
            raise AuthError("invalid auth token")
        if record.get("revoked"):
            raise AuthError("auth token revoked")
        expires_at = parse_iso(str(record.get("expires_at")))
        if datetime.now() > expires_at:
            raise AuthError("auth token expired")
        return record

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "tokens": {}}
        try:
            payload = read_json(self.path)
        except json.JSONDecodeError:
            return {"version": 1, "tokens": {}}
        payload.setdefault("version", 1)
        payload.setdefault("tokens", {})
        return payload

    def _save(self, registry: dict[str, Any]) -> None:
        write_json(self.path, registry)

    def _public_record(self, record: dict[str, Any]) -> dict[str, Any]:
        public = {
            "task_id": record.get("task_id"),
            "env_id": record.get("env_id", self.env_id),
            "track": record.get("track"),
            "created_at": record.get("created_at"),
            "expires_at": record.get("expires_at"),
            "max_new_games": record.get("max_new_games"),
            "used_new_games": record.get("used_new_games"),
            "remaining_new_games": int(record.get("max_new_games", 0)) - int(record.get("used_new_games", 0)),
            "game_ids": list(record.get("game_ids", [])),
            "verified_game_ids": list(record.get("verified_game_ids", [])),
            "goal": record.get("goal"),
            "tick_budget": record.get("tick_budget"),
            "tick_budget_type": "lifetime",
            "soft_stop_tick": record.get("soft_stop_tick"),
            "soft_stop_scoring": normalize_soft_stop_scoring(record.get("soft_stop_scoring")),
            "per_run_tick_budget": record.get("per_run_tick_budget"),
            "token_role": record.get("token_role", "official"),
            "official": bool(record.get("official", True)),
            "scoring": record.get("scoring"),
        }
        public.update(self._public_policy(record))
        return public

    def _public_policy(self, record: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _game_private_policy(self, record: dict[str, Any]) -> dict[str, Any]:
        return {}


class PersistedGameStore:
    def __init__(self, games_root: Path, adapter: EnvironmentAdapter) -> None:
        self.games_root = games_root
        self.adapter = adapter
        self.games_root.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Any] = {}
        self._lock = threading.RLock()

    def create_game(
        self,
        label: str | None = None,
        *,
        token_info: dict[str, Any] | None = None,
        game_id: str | None = None,
        **options: Any,
    ) -> dict[str, Any]:
        with self._lock:
            game_id = safe_game_id(game_id) if game_id else self.new_game_id()
            session_dir = self._session_dir(game_id)
            session_dir.mkdir(parents=True, exist_ok=False)
            state_path = session_dir / "state.json"
            session = self.adapter.new_session(
                state_path,
                token_info=token_info,
                options=options,
            )
            self.adapter.save_session(session)
            self._sessions[game_id] = session

            created_at = now_iso()
            is_official = bool(token_info) and bool(token_info.get("official", True))
            session_meta = {
                "id": game_id,
                "env_id": token_info.get("env_id", self.adapter.env_id) if token_info else self.adapter.env_id,
                "track": token_info.get("track") if token_info else None,
                "label": label or game_id,
                "created_at": created_at,
                "updated_at": created_at,
                "state_path": str(state_path),
                "official": is_official,
                "token_role": token_info.get("token_role") if token_info else None,
                "scoring": token_info.get("scoring") if token_info else None,
                "task_id": token_info.get("task_id") if token_info else None,
                "token_hash": token_info.get("token_hash") if token_info else None,
                "submitted": False,
                "submitted_at": None,
            }
            session_meta.update(self.adapter.session_metadata(session))
            trajectory = {
                "version": 1,
                "session": session_meta,
                "entries": [
                    self._entry(
                        index=0,
                        command="__init__",
                        output="new game",
                        observation=self.adapter.observe(session),
                        reward=int(self.adapter.score(session)["reward"]),
                        done=False,
                    )
                ],
            }
            write_json(self._trajectory_path(game_id), trajectory)
            return self.get_game(game_id)

    @staticmethod
    def new_game_id() -> str:
        return f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def list_games(self) -> list[dict[str, Any]]:
        with self._lock:
            games: list[dict[str, Any]] = []
            for child in self.games_root.iterdir():
                if not child.is_dir() or not GAME_ID_RE.match(child.name):
                    continue
                trajectory_path = child / "trajectory.json"
                if not trajectory_path.exists():
                    continue
                try:
                    games.append(self._summary(read_json(trajectory_path)))
                except (OSError, json.JSONDecodeError, KeyError):
                    continue
            games.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
            return games

    def get_game(self, game_id: str) -> dict[str, Any]:
        with self._lock:
            trajectory = self._load_trajectory(game_id)
            session = self._load_session(game_id)
            verification_path = self._verification_path(game_id)
            verification = None
            if verification_path.exists():
                try:
                    verification = read_json(verification_path)
                except (OSError, json.JSONDecodeError):
                    verification = None
            return {
                "summary": self._summary(trajectory),
                "current": self.adapter.observe(session),
                "trajectory": trajectory,
                "verification": verification,
            }

    def step_game(self, game_id: str, command: str) -> dict[str, Any]:
        command = command.strip()
        if not command:
            raise ValueError("command is empty")
        with self._lock:
            trajectory = self._load_trajectory(game_id)
            if self._is_submitted(trajectory):
                raise ValueError("official game already submitted; create a new official game for another attempt")
            session = self._load_session(game_id)
            result = self.adapter.step(session, command)
            self.adapter.save_session(session)
            entry = self._entry(
                index=len(trajectory["entries"]),
                command=command,
                output=result.output,
                observation=self.adapter.observe(session),
                reward=result.reward,
                done=result.done,
            )
            trajectory["entries"].append(entry)
            trajectory["session"]["updated_at"] = entry["wall_time"]
            write_json(self._trajectory_path(game_id), trajectory)
            return {
                "summary": self._summary(trajectory),
                "entry": entry,
                "current": entry["observation"],
                "trajectory": trajectory,
            }

    def run_commands(self, game_id: str, commands: list[str]) -> dict[str, Any]:
        entries = []
        for raw in commands:
            command = raw.strip()
            if not command or command.startswith("#"):
                continue
            result = self.step_game(game_id, command)
            entries.append(result["entry"])
            if result["entry"]["done"]:
                break
        game = self.get_game(game_id)
        game["entries"] = entries
        return game

    def list_available(self, game_id: str, kind: str) -> str:
        with self._lock:
            session = self._load_session(game_id)
            return self.adapter.list_available(session, kind)

    def score_game(self, game_id: str, goal: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            session = self._load_session(game_id)
            return self.adapter.score(session, goal)

    def verify_game(
        self,
        game_id: str,
        *,
        token_info: dict[str, Any],
        goal: dict[str, Any] | None = None,
        tick_budget: int | None = None,
        lifetime_tick_budget: int | None = None,
        soft_stop_tick: int | None = None,
        per_run_tick_budget: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            trajectory = self._load_trajectory(game_id)
            session_info = trajectory.get("session", {})
            if not session_info.get("official"):
                raise AuthError("only token-created official games can be verified")
            if session_info.get("token_hash") != token_info.get("token_hash"):
                raise AuthError("token does not match this game")
            verification_path = self._verification_path(game_id)
            if self._is_submitted(trajectory):
                if verification_path.exists():
                    return read_json(verification_path)
                raise ValueError("official game already submitted")
            session = self._load_session(game_id)
            token_goal = token_info.get("goal") or None
            request_goal = goal or None
            final_goal_dict = dict(request_goal or {})
            if token_goal:
                final_goal_dict.update(token_goal)

            budget_policy = {
                "primary_metric": "lifetime_tick",
                "primary_token_key": "tick_budget",
                "primary_goal_keys": ("lifetime_tick_budget", "tick_budget"),
                "primary_goal_emit_key": "tick_budget",
                "soft_stop_metric": "lifetime_tick",
                "soft_stop_token_key": "soft_stop_tick",
                "soft_stop_goal_keys": ("soft_stop_tick",),
                "secondary_metric": "tick",
                "secondary_token_key": "per_run_tick_budget",
                "secondary_goal_keys": ("per_run_tick_budget",),
                "secondary_goal_emit_key": "per_run_tick_budget",
                "legacy_tick_budget_type": "lifetime",
            }
            budget_policy.update(self.adapter.budget_policy())
            primary_metric = str(budget_policy["primary_metric"])
            primary_token_key = str(budget_policy["primary_token_key"])
            primary_goal_keys = tuple(budget_policy["primary_goal_keys"])
            primary_goal_emit_key = str(budget_policy["primary_goal_emit_key"])
            soft_stop_metric = str(budget_policy["soft_stop_metric"])
            soft_stop_token_key = str(budget_policy["soft_stop_token_key"])
            soft_stop_goal_keys = tuple(budget_policy["soft_stop_goal_keys"])
            secondary_metric = budget_policy.get("secondary_metric")
            secondary_token_key = str(budget_policy["secondary_token_key"])
            secondary_goal_keys = tuple(budget_policy["secondary_goal_keys"])
            secondary_goal_emit_key = str(budget_policy["secondary_goal_emit_key"])
            legacy_tick_budget_type = str(budget_policy["legacy_tick_budget_type"])

            def first_present(mapping: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
                if not mapping:
                    return None
                for key in keys:
                    if mapping.get(key) is not None:
                        return mapping.get(key)
                return None

            token_primary_budget = token_info.get(primary_token_key)
            if token_primary_budget is None and primary_token_key != "tick_budget":
                token_primary_budget = token_info.get("tick_budget")
            if token_primary_budget is None and token_goal:
                token_primary_budget = first_present(token_goal, primary_goal_keys)
            request_primary_budget = lifetime_tick_budget
            if request_primary_budget is None:
                request_primary_budget = tick_budget
            if request_primary_budget is None and request_goal:
                request_primary_budget = first_present(request_goal, primary_goal_keys)

            token_soft_stop = token_info.get(soft_stop_token_key)
            if token_soft_stop is None and soft_stop_token_key != "soft_stop_tick":
                token_soft_stop = token_info.get("soft_stop_tick")
            if token_soft_stop is None and token_goal:
                token_soft_stop = first_present(token_goal, soft_stop_goal_keys)
            request_soft_stop = soft_stop_tick
            if request_soft_stop is None and request_goal:
                request_soft_stop = first_present(request_goal, soft_stop_goal_keys)

            token_secondary_budget = token_info.get(secondary_token_key)
            if token_secondary_budget is None and secondary_token_key != "per_run_tick_budget":
                token_secondary_budget = token_info.get("per_run_tick_budget")
            if token_secondary_budget is None and token_goal:
                token_secondary_budget = first_present(token_goal, secondary_goal_keys)
            request_secondary_budget = per_run_tick_budget
            if request_secondary_budget is None and request_goal:
                request_secondary_budget = first_present(request_goal, secondary_goal_keys)

            if token_primary_budget is not None:
                final_primary_budget = int(token_primary_budget)
                primary_budget_source = "token"
            elif request_primary_budget is not None:
                final_primary_budget = int(request_primary_budget)
                primary_budget_source = "request"
            else:
                final_primary_budget = None
                primary_budget_source = "none"
            if final_primary_budget is not None:
                final_goal_dict[primary_goal_emit_key] = final_primary_budget
            if token_soft_stop is not None:
                final_soft_stop_tick = int(token_soft_stop)
                soft_stop_tick_source = "token"
            elif request_soft_stop is not None:
                final_soft_stop_tick = int(request_soft_stop)
                soft_stop_tick_source = "request"
            else:
                final_soft_stop_tick = None
                soft_stop_tick_source = "none"
            if token_secondary_budget is not None:
                final_secondary_budget = int(token_secondary_budget)
                secondary_budget_source = "token"
            elif request_secondary_budget is not None:
                final_secondary_budget = int(request_secondary_budget)
                secondary_budget_source = "request"
            else:
                final_secondary_budget = None
                secondary_budget_source = "none"
            if final_secondary_budget is not None:
                final_goal_dict[secondary_goal_emit_key] = final_secondary_budget
            final_goal = final_goal_dict or None

            if token_goal and request_goal:
                goal_source = "merged_token_priority"
            elif token_goal:
                goal_source = "token"
            elif request_goal:
                goal_source = "request"
            else:
                goal_source = "none"
            request_tick_budget_ignored = token_primary_budget is not None and request_primary_budget is not None
            tick_budget_conflict = (
                request_tick_budget_ignored
                and int(request_primary_budget) != int(token_primary_budget)
            )
            request_soft_stop_tick_ignored = (
                token_soft_stop is not None
                and request_soft_stop is not None
            )
            soft_stop_tick_conflict = (
                request_soft_stop_tick_ignored
                and int(request_soft_stop) != int(token_soft_stop)
            )
            final_soft_stop_scoring = normalize_soft_stop_scoring(token_info.get("soft_stop_scoring"))
            request_per_run_tick_budget_ignored = (
                token_secondary_budget is not None
                and request_secondary_budget is not None
            )
            per_run_tick_budget_conflict = (
                request_per_run_tick_budget_ignored
                and int(request_secondary_budget) != int(token_secondary_budget)
            )
            policy = {
                "goal_source": goal_source,
                "request_goal": request_goal,
                "token_goal": token_goal,
                "budget_metric": primary_metric,
                "primary_budget_metric": primary_metric,
                "secondary_budget_metric": secondary_metric,
                "soft_stop_metric": soft_stop_metric,
                "tick_budget_type": legacy_tick_budget_type,
                "tick_budget_source": primary_budget_source,
                "request_tick_budget": request_primary_budget,
                "token_tick_budget": token_primary_budget,
                "request_tick_budget_ignored": request_tick_budget_ignored,
                "tick_budget_conflict": tick_budget_conflict,
                "lifetime_tick_budget_source": primary_budget_source,
                "request_lifetime_tick_budget": request_primary_budget,
                "token_lifetime_tick_budget": token_primary_budget,
                "request_lifetime_tick_budget_ignored": request_tick_budget_ignored,
                "lifetime_tick_budget_conflict": tick_budget_conflict,
                "soft_stop_tick_source": soft_stop_tick_source,
                "request_soft_stop_tick": request_soft_stop,
                "token_soft_stop_tick": token_soft_stop,
                "request_soft_stop_tick_ignored": request_soft_stop_tick_ignored,
                "soft_stop_tick_conflict": soft_stop_tick_conflict,
                "soft_stop_scoring": final_soft_stop_scoring,
                "per_run_tick_budget_source": secondary_budget_source,
                "request_per_run_tick_budget": request_secondary_budget,
                "token_per_run_tick_budget": token_secondary_budget,
                "request_per_run_tick_budget_ignored": request_per_run_tick_budget_ignored,
                "per_run_tick_budget_conflict": per_run_tick_budget_conflict,
            }
            score = self.adapter.score(session, final_goal)
            metrics = self.adapter.metrics(session)
            primary_used = int(metrics[primary_metric])
            soft_stop_used = int(metrics[soft_stop_metric])
            secondary_used = (
                int(metrics[str(secondary_metric)])
                if secondary_metric and str(secondary_metric) in metrics
                else None
            )
            tick_budget_exceeded = (
                final_primary_budget is not None
                and primary_used > int(final_primary_budget)
            )
            per_run_tick_budget_exceeded = (
                final_secondary_budget is not None
                and secondary_used is not None
                and secondary_used > int(final_secondary_budget)
            )
            budget_exceeded = tick_budget_exceeded or per_run_tick_budget_exceeded
            soft_stop_exceeded = (
                final_soft_stop_tick is not None
                and soft_stop_used > int(final_soft_stop_tick)
            )
            soft_stop_overrun = (
                max(0, soft_stop_used - int(final_soft_stop_tick))
                if final_soft_stop_tick is not None
                else None
            )
            soft_stop_score_value = soft_stop_score(
                scoring=final_soft_stop_scoring,
                used=soft_stop_used,
                soft_stop=final_soft_stop_tick,
                hard_limit=final_primary_budget,
            )
            reward = 0 if budget_exceeded else int(score["reward"])
            goal_completion = score_goal_completion(score)
            goal_achieved = goal_completion["achieved"]
            accepted = not budget_exceeded
            submitted_at = now_iso()
            session_info["submitted"] = True
            session_info["submitted_at"] = submitted_at
            session_info["updated_at"] = submitted_at
            verification = {
                "accepted": accepted,
                "outcome": verification_outcome(accepted=accepted, goal_achieved=goal_achieved),
                "goalAchieved": goal_achieved,
                "goalCompletion": goal_completion,
                "verified_at": submitted_at,
                "submitted": True,
                "submitted_at": submitted_at,
                "game_id": game_id,
                "env_id": session_info.get("env_id", token_info.get("env_id", self.adapter.env_id)),
                "track": session_info.get("track", token_info.get("track")),
                "task_id": session_info.get("task_id"),
                "official": True,
                "token_role": session_info.get("token_role", token_info.get("token_role")),
                "scoring": session_info.get("scoring", token_info.get("scoring")),
                "token_hash": session_info.get("token_hash"),
                "trajectory_hash": trajectory_hash(trajectory),
                "reward": reward,
                "score": score,
                "goal": final_goal,
                "policy": policy,
                "budget": {
                    "metric": primary_metric,
                    "used": primary_used,
                    "limit": final_primary_budget,
                    "exceeded": tick_budget_exceeded,
                    "soft_stop_metric": soft_stop_metric,
                    "soft_stop": final_soft_stop_tick,
                    "soft_stop_used": soft_stop_used,
                    "soft_stop_exceeded": soft_stop_exceeded,
                    "soft_stop_scoring": final_soft_stop_scoring,
                },
                "tickBudget": final_primary_budget,
                "tickBudgetType": legacy_tick_budget_type,
                "tickBudgetUsed": primary_used,
                "tickBudgetExceeded": tick_budget_exceeded,
                "budgetExceeded": budget_exceeded,
                "lifetimeTickBudget": final_primary_budget,
                "lifetimeTickBudgetUsed": primary_used,
                "lifetimeTickBudgetExceeded": tick_budget_exceeded,
                "softStopTick": final_soft_stop_tick,
                "softStopUsed": soft_stop_used,
                "softStopExceeded": soft_stop_exceeded,
                "softStopOverrun": soft_stop_overrun,
                "softStopScoring": final_soft_stop_scoring,
                "softStopScore": soft_stop_score_value,
                "complianceScore": soft_stop_score_value,
                "compliance": {
                    "softStop": {
                        "metric": soft_stop_metric,
                        "used": soft_stop_used,
                        "limit": final_soft_stop_tick,
                        "exceeded": soft_stop_exceeded,
                        "overrun": soft_stop_overrun,
                        "scoring": final_soft_stop_scoring,
                        "score": soft_stop_score_value,
                    }
                },
                "perRunTickBudget": final_secondary_budget,
                "perRunTickBudgetUsed": secondary_used,
                "perRunTickBudgetExceeded": per_run_tick_budget_exceeded,
                "trajectoryMetrics": self.adapter.trajectory_metrics(trajectory),
                "entryCount": len(trajectory.get("entries", [])),
                "final": self.adapter.observe(session, include_text=False),
            }
            write_json(verification_path, verification)
            write_json(self._trajectory_path(game_id), trajectory)
            return verification

    def _load_session(self, game_id: str) -> Any:
        game_id = safe_game_id(game_id)
        if game_id in self._sessions:
            return self._sessions[game_id]
        state_path = self._state_path(game_id)
        if not state_path.exists():
            raise KeyError(game_id)
        session = self.adapter.load_session(state_path)
        self._sessions[game_id] = session
        return session

    def _load_trajectory(self, game_id: str) -> dict[str, Any]:
        game_id = safe_game_id(game_id)
        path = self._trajectory_path(game_id)
        if path.exists():
            return read_json(path)
        session = self._load_session(game_id)
        created_at = now_iso()
        trajectory = {
            "version": 1,
            "session": {
                "id": game_id,
                "env_id": self.adapter.env_id,
                "track": None,
                "label": game_id,
                "created_at": created_at,
                "updated_at": created_at,
                "state_path": str(self._state_path(game_id)),
            },
            "entries": [
                self._entry(
                    index=0,
                    command="__load__",
                    output="trajectory rebuilt from state",
                    observation=self.adapter.observe(session),
                    reward=int(self.adapter.score(session)["reward"]),
                    done=False,
                )
            ],
        }
        write_json(path, trajectory)
        return trajectory

    def _summary(self, trajectory: dict[str, Any]) -> dict[str, Any]:
        session = trajectory["session"]
        entries = trajectory.get("entries", [])
        last = entries[-1] if entries else {}
        observation = last.get("observation", {})
        score = observation.get("score", {})
        summary = {
            "id": session["id"],
            "env_id": session.get("env_id", self.adapter.env_id),
            "track": session.get("track"),
            "label": session.get("label") or session["id"],
            "official": bool(session.get("official", False)),
            "token_role": session.get("token_role"),
            "scoring": session.get("scoring"),
            "task_id": session.get("task_id"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "submitted": self._is_submitted(trajectory),
            "submitted_at": session.get("submitted_at"),
            "entry_count": len(entries),
            "last_command": last.get("command"),
            "done": bool(last.get("done", False)),
            "reward": score.get("reward"),
        }
        summary.update(self.adapter.summary_fields(observation, score))
        return summary

    def _entry(
        self,
        *,
        index: int,
        command: str,
        output: str,
        observation: dict[str, Any],
        reward: int,
        done: bool,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "wall_time": now_iso(),
            "command": command,
            "output": output,
            "observation": observation,
            "reward": reward,
            "done": done,
        }

    def _session_dir(self, game_id: str) -> Path:
        return self.games_root / safe_game_id(game_id)

    def _state_path(self, game_id: str) -> Path:
        return self._session_dir(game_id) / "state.json"

    def _trajectory_path(self, game_id: str) -> Path:
        return self._session_dir(game_id) / "trajectory.json"

    def _verification_path(self, game_id: str) -> Path:
        return self._session_dir(game_id) / "verification.json"

    def _is_submitted(self, trajectory: dict[str, Any]) -> bool:
        session = trajectory.get("session", {})
        if not bool(session.get("official", False)):
            return False
        if bool(session.get("submitted", False)):
            return True
        game_id = str(session.get("id", ""))
        return bool(game_id) and self._verification_path(game_id).exists()


CreateGameOptions = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class EnvironmentServerSpec:
    env_id: str
    display_name: str
    default_data_dir: Path
    default_token_path: Path
    store_factory: Callable[[Path], GameStoreProtocol]
    token_registry_factory: Callable[[Path], TokenRegistryProtocol]
    load_index_html: Callable[[], str]
    server_version: str = "PlaygroundServer/0.1"
    token_headers: tuple[str, ...] = ("X-Playground-Token",)
    create_game_options: CreateGameOptions | None = None


def make_handler(
    store: GameStoreProtocol,
    *,
    spec: EnvironmentServerSpec,
    token_registry: TokenRegistryProtocol | None = None,
    require_token: bool = False,
) -> type[BaseHTTPRequestHandler]:
    class PlaygroundHandler(BaseHTTPRequestHandler):
        server_version = spec.server_version

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            try:
                if parsed.path == "/":
                    self._send_html(spec.load_index_html())
                elif parsed.path == "/api/health":
                    self._send_json(
                        {
                            "ok": True,
                            "env_id": spec.env_id,
                            "display_name": spec.display_name,
                            "games_root": str(store.games_root),
                        }
                    )
                elif parsed.path == "/api/auth/status":
                    token = self._auth_token(required=True)
                    if not token_registry:
                        raise AuthError("auth tokens are not configured")
                    self._send_json(token_registry.status(token))
                elif parsed.path == "/api/games":
                    self._send_json(store.list_games())
                else:
                    match = re.fullmatch(r"/api/games/([^/]+)(?:/(trajectory|state))?", parsed.path)
                    list_match = re.fullmatch(r"/api/games/([^/]+)/list/([^/]+)", parsed.path)
                    if list_match:
                        game_id, kind = list_match.groups()
                        decoded_kind = urllib.parse.unquote(kind)
                        self._send_json({"kind": decoded_kind, "output": store.list_available(game_id, decoded_kind)})
                        return
                    if not match:
                        self._send_error(HTTPStatus.NOT_FOUND, "not found")
                        return
                    game_id = match.group(1)
                    kind = match.group(2)
                    game = store.get_game(game_id)
                    if kind == "trajectory":
                        self._send_json(game["trajectory"])
                    elif kind == "state":
                        self._send_json(game["current"])
                    else:
                        self._send_json(game)
            except KeyError:
                self._send_error(HTTPStatus.NOT_FOUND, "game not found")
            except AuthError as exc:
                self._send_error(HTTPStatus.UNAUTHORIZED, str(exc))
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            except OSError as exc:
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            try:
                payload = self._read_json()
                if parsed.path == "/api/games":
                    label = payload.get("label")
                    token = self._auth_token(required=require_token)
                    token_info = None
                    game_id = store.new_game_id()
                    if token:
                        if not token_registry:
                            raise AuthError("auth tokens are not configured")
                        token_info = token_registry.consume_new_game(token, game_id)
                    create_options = spec.create_game_options(payload) if spec.create_game_options else {}
                    self._send_json(
                        store.create_game(
                            label=label,
                            token_info=token_info,
                            game_id=game_id,
                            **create_options,
                        ),
                        HTTPStatus.CREATED,
                    )
                    return
                match = re.fullmatch(r"/api/games/([^/]+)/(command|commands)", parsed.path)
                score_match = re.fullmatch(r"/api/games/([^/]+)/score", parsed.path)
                verify_match = re.fullmatch(r"/api/games/([^/]+)/verify", parsed.path)
                if verify_match:
                    if not token_registry:
                        raise AuthError("auth tokens are not configured")
                    game_id = verify_match.group(1)
                    token = self._auth_token(required=True)
                    token_info = token_registry.require_game(token, game_id)
                    verification = store.verify_game(
                        game_id,
                        token_info=token_info,
                        goal=payload.get("goal"),
                        tick_budget=payload.get("tick_budget"),
                        lifetime_tick_budget=payload.get("lifetime_tick_budget"),
                        soft_stop_tick=payload.get("soft_stop_tick"),
                        per_run_tick_budget=payload.get("per_run_tick_budget"),
                    )
                    token_registry.mark_verified(token, game_id)
                    self._send_json(verification)
                    return
                if score_match:
                    goal = payload.get("goal", payload or None)
                    self._send_json(store.score_game(score_match.group(1), goal))
                    return
                if not match:
                    self._send_error(HTTPStatus.NOT_FOUND, "not found")
                    return
                game_id, action = match.groups()
                self._authorize_game_write(game_id)
                if action == "command":
                    self._send_json(store.step_game(game_id, str(payload.get("command", ""))))
                else:
                    commands = payload.get("commands")
                    if isinstance(commands, str):
                        commands = commands.splitlines()
                    if not isinstance(commands, list):
                        raise ValueError("commands must be a list or newline string")
                    self._send_json(store.run_commands(game_id, [str(command) for command in commands]))
            except json.JSONDecodeError:
                self._send_error(HTTPStatus.BAD_REQUEST, "invalid json")
            except KeyError:
                self._send_error(HTTPStatus.NOT_FOUND, "game not found")
            except AuthError as exc:
                self._send_error(HTTPStatus.UNAUTHORIZED, str(exc))
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

        def log_message(self, format: str, *args: Any) -> None:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {self.address_string()} {format % args}")

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _auth_token(self, *, required: bool = False) -> str | None:
            auth_header = self.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:].strip()
            else:
                token = ""
                for header in spec.token_headers:
                    token = self.headers.get(header, "").strip()
                    if token:
                        break
            if required and not token:
                raise AuthError("missing auth token")
            return token or None

        def _authorize_game_write(self, game_id: str) -> None:
            game = store.get_game(game_id)
            official = bool(game.get("summary", {}).get("official"))
            if not official and not require_token:
                return
            if not token_registry:
                raise AuthError("auth tokens are not configured")
            token = self._auth_token(required=True)
            token_registry.require_game(token, game_id)

        def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            self._send_json({"error": message}, status)

    return PlaygroundHandler


def serve_main(spec: EnvironmentServerSpec, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{spec.display_name} replay server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=spec.default_data_dir)
    parser.add_argument("--token-file", type=Path, default=spec.default_token_path)
    parser.add_argument(
        "--require-token",
        action="store_true",
        help="Require an auth token for creating games and mutating official games.",
    )
    args = parser.parse_args(argv)

    store = spec.store_factory(args.data_dir)
    token_registry = spec.token_registry_factory(args.token_file)
    handler = make_handler(store, spec=spec, token_registry=token_registry, require_token=args.require_token)
    httpd = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"{spec.display_name} replay server: http://{args.host}:{args.port}")
    print(f"Environment: {spec.env_id}")
    print(f"Game trajectories: {store.games_root}")
    print(f"Auth tokens: {token_registry.path}")
    print(f"Require token: {args.require_token}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server.")
    finally:
        httpd.server_close()
    return 0


__all__ = [
    "AuthError",
    "EnvironmentAdapter",
    "EnvironmentServerSpec",
    "GameStoreProtocol",
    "PersistedGameStore",
    "StepOutcome",
    "TokenRegistryBase",
    "TokenRegistryProtocol",
    "make_handler",
    "now_iso",
    "normalize_soft_stop_scoring",
    "parse_iso",
    "read_json",
    "safe_game_id",
    "serve_main",
    "soft_stop_score",
    "token_hash",
    "write_json",
]
