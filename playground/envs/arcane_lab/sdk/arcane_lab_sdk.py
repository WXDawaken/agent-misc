from __future__ import annotations

import copy
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
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "arcane_lab" and ROOT.parent.name == "envs" else ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import game  # noqa: E402


DEFAULT_STATE = PLAYGROUND_ROOT / "saves" / "sdk_state.json"


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


def _goal_status_achieved(status: Any) -> bool:
    if isinstance(status, bool):
        return status
    if isinstance(status, dict) and "achieved" in status:
        return bool(status["achieved"])
    return bool(status)


def goal_completion(goal_status: dict[str, Any]) -> dict[str, Any]:
    failed = [
        name
        for name, status in goal_status.items()
        if not _goal_status_achieved(status)
    ]
    total = len(goal_status)
    return {
        "achieved": None if total == 0 else not failed,
        "achieved_count": total - len(failed),
        "total": total,
        "failed": failed,
    }


class ArcaneLabSDK:
    """Small programmatic interface for Arcane Lab agent play.

    The SDK intentionally mirrors the benchmark pattern from RuneBench:
    agents can inspect state, issue compact actions, collect a transcript,
    and export tracking/reward data for a verifier.
    """

    def __init__(
        self,
        state_path: str | Path | None = None,
        *,
        new: bool = False,
        autosave: bool = False,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> None:
        self.data = game.load_data()
        self.state_path = self._resolve_path(state_path) if state_path else DEFAULT_STATE
        self.autosave = autosave
        self.samples: list[dict[str, Any]] = []
        self.transcript: list[dict[str, Any]] = []
        self.state = game.load_state(self.state_path, self.data, force_new=new)
        if (
            crit_mode
            or crit_seed
            or crit_charge_bonus is not None
            or crit_random_chance is not None
            or crit_random_bonus is not None
        ):
            game.configure_crit_state(
                self.state,
                mode=crit_mode,
                seed=crit_seed,
                charge_bonus=crit_charge_bonus,
                random_chance=crit_random_chance,
                random_bonus=crit_random_bonus,
            )
        game.check_storylines(self.state, self.data)
        self._sample("init", "session started")

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        return _resolve_workspace_path(path)

    def reset(
        self,
        *,
        save: bool | None = None,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> dict[str, Any]:
        current_crit = game.normalize_crit_state(self.state)
        self.state = game.fresh_state(
            self.data,
            crit_mode=crit_mode or current_crit.get("mode"),
            crit_seed=crit_seed if crit_seed is not None else current_crit.get("seed"),
            crit_charge_bonus=crit_charge_bonus if crit_charge_bonus is not None else current_crit.get("charge_bonus"),
            crit_random_chance=crit_random_chance if crit_random_chance is not None else current_crit.get("random_chance"),
            crit_random_bonus=crit_random_bonus if crit_random_bonus is not None else current_crit.get("random_bonus"),
        )
        game.check_storylines(self.state, self.data)
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
            "tick": self.state["tick"],
            "command": command,
            "output": output,
        })
        self._sample(command, output)
        return StepResult(
            command=command,
            output=output,
            observation=self.observe(include_text=False),
            reward=self.score()["reward"],
            done=not keep_going,
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
        attack, defense = game.combat_stats(self.state, self.data)
        known_spells = sorted(game.known_spell_ids(self.state, self.data))
        known_recipes = sorted(game.known_recipe_ids(self.state, self.data))
        next_goals = game.visible_storyline_summaries(self.state, self.data, limit=6)
        completed_storylines = set(self.state["completed_storylines"])
        hidden_goal_count = sum(
            1
            for storyline in self.data["storylines"]
            if (
                storyline["id"] not in completed_storylines
                and not game.storyline_is_visible(self.state, self.data, storyline)
            )
        )
        areas = game.index_by_id(self.data["areas"])
        observation = {
            "run": self.state["run"],
            "tick": self.state["tick"],
            "lifetime_tick": self.state.get("lifetime_tick", self.state["tick"]),
            "retirements": self.state["retirements"],
            "insight": self.state["insight"],
            "mana": {
                "current": round(float(self.state["mana"]), 3),
                "max": round(float(game.max_mana(self.state, self.data)), 3),
                "rate": round(float(game.mana_rate(self.state, self.data)), 3),
            },
            "hp": {
                "current": round(float(self.state["hp"]), 3),
                "max": round(float(game.max_hp(self.state, self.data)), 3),
            },
            "combat": {
                "attack": round(float(attack), 3),
                "defense": round(float(defense), 3),
            },
            "resources": copy.deepcopy(self.state["resources"]),
            "elements": copy.deepcopy(self.state["elements"]),
            "wizards": self.state["wizards"],
            "assignments": copy.deepcopy(self.state["assignments"]),
            "buffs": copy.deepcopy(self.state.get("buffs", {})),
            "last_action": copy.deepcopy(self.state.get("last_action")),
            "action_costs": copy.deepcopy(game.ACTION_TICKS),
            "crit": game.crit_public_state(self.state, self.data),
            "equipment": copy.deepcopy(self.state["equipment"]),
            "equipment_spares": copy.deepcopy(self.state.get("equipment_spares", {})),
            "equipment_levels": copy.deepcopy(self.state.get("equipment_levels", {})),
            "areas": {
                area_id: {
                    "progress": self.state["area_progress"].get(area_id, 0),
                    "clears": self.state["area_clears"].get(area_id, 0),
                    "requires_attack": areas[area_id]["requires_attack"],
                    "requires_defense": areas[area_id]["requires_defense"],
                    "clears_required": areas[area_id]["clears_required"],
                    "boss": game.public_boss(areas[area_id]),
                }
                for area_id in self.state["unlocked_areas"]
            },
            "known_spells": known_spells,
            "known_recipes": known_recipes,
            "completed_storylines": list(self.state["completed_storylines"]),
            "retirement_unlocked": self.state["retirement_unlocked"],
            "next_goals": next_goals,
            "hidden_goal_count": hidden_goal_count,
            "score": self.score(),
        }
        if include_text:
            observation["status_text"] = game.cmd_status(self.state, self.data)
        return observation

    def list_available(self, kind: str) -> str:
        return game.cmd_list(kind, self.state, self.data)

    def score(self, goal: dict[str, Any] | None = None) -> dict[str, Any]:
        metrics = self.metrics()
        reward = (
            metrics["storylines_completed"] * 1000
            + metrics["total_area_clears"] * 180
            + metrics["total_element_levels"] * 60
            + metrics["equipment_count"] * 120
            + metrics["equipment_enhancement_levels"] * 60
            + metrics["wizards"] * 80
            + metrics["insight"] * 500
            + metrics["coins"]
            + metrics["resource_units"] * 5
        )
        goal_bonus = 0
        goal_status: dict[str, Any] = {}
        if goal:
            storyline = goal.get("storyline")
            area = goal.get("area")
            recipe = goal.get("recipe")
            assignment = goal.get("assignment")
            wizards = goal.get("wizards")
            retirements = goal.get("retirements")
            insight = goal.get("insight")
            run = goal.get("run")
            unlocked_areas = goal.get("unlocked_areas") or []
            tick_budget = goal.get("tick_budget")
            explicit_lifetime_tick_budget = goal.get("lifetime_tick_budget")
            lifetime_tick_budget = explicit_lifetime_tick_budget
            if lifetime_tick_budget is None:
                lifetime_tick_budget = tick_budget
            per_run_tick_budget = goal.get("per_run_tick_budget")
            area_progress = goal.get("area_progress")
            if storyline:
                achieved = storyline in self.state["completed_storylines"]
                goal_status[f"storyline:{storyline}"] = achieved
                goal_bonus += 5000 if achieved else 0
            if area:
                clears = self.state["area_clears"].get(area, 0)
                target = int(goal.get("area_clears", 1))
                achieved = clears >= target
                goal_status[f"area:{area}"] = {"clears": clears, "target": target, "achieved": achieved}
                goal_bonus += 2500 if achieved else clears * 300
            if area_progress:
                area_id = str(area_progress.get("area", ""))
                target = int(area_progress.get("target", 1))
                areas = game.index_by_id(self.data["areas"])
                clears_required = int(areas.get(area_id, {}).get("clears_required", 1))
                clears = int(self.state["area_clears"].get(area_id, 0))
                current_progress = int(self.state["area_progress"].get(area_id, 0))
                progress_steps = clears * clears_required + current_progress
                achieved = progress_steps >= target
                goal_status[f"area_progress:{area_id}"] = {
                    "progress_steps": progress_steps,
                    "target": target,
                    "clears": clears,
                    "current_progress": current_progress,
                    "clears_required": clears_required,
                    "achieved": achieved,
                }
                goal_bonus += 1000 if achieved else progress_steps * 150
            if recipe:
                owned = self.state["equipment"].get(recipe, 0)
                target = int(goal.get("recipe_count", 1))
                achieved = owned >= target
                goal_status[f"recipe:{recipe}"] = {"owned": owned, "target": target, "achieved": achieved}
                goal_bonus += 2000 if achieved else owned * 250
            if assignment:
                assigned = self.state.get("assignments", {}).get(assignment, 0)
                target = int(goal.get("assignment_count", 1))
                achieved = assigned >= target
                goal_status[f"assignment:{assignment}"] = {
                    "assigned": assigned,
                    "target": target,
                    "achieved": achieved,
                }
                goal_bonus += 1500 if achieved else assigned * 200
            if wizards is not None:
                target = int(wizards)
                owned = int(self.state.get("wizards", 0))
                achieved = owned >= target
                goal_status["wizards"] = {"owned": owned, "target": target, "achieved": achieved}
                goal_bonus += 1200 if achieved else owned * 150
            if retirements is not None:
                target = int(retirements)
                owned = int(self.state.get("retirements", 0))
                achieved = owned >= target
                goal_status["retirements"] = {"owned": owned, "target": target, "achieved": achieved}
                goal_bonus += 1800 if achieved else owned * 300
            if insight is not None:
                target = int(insight)
                owned = int(self.state.get("insight", 0))
                achieved = owned >= target
                goal_status["insight"] = {"owned": owned, "target": target, "achieved": achieved}
                goal_bonus += 1800 if achieved else owned * 80
            if run is not None:
                target = int(run)
                owned = int(self.state.get("run", 1))
                achieved = owned >= target
                goal_status["run"] = {"owned": owned, "target": target, "achieved": achieved}
                goal_bonus += 1000 if achieved else max(0, owned - 1) * 200
            for area_id in unlocked_areas:
                achieved = area_id in self.state.get("unlocked_areas", [])
                goal_status[f"unlocked_area:{area_id}"] = achieved
                goal_bonus += 500 if achieved else 0
            if lifetime_tick_budget is not None:
                budget = int(lifetime_tick_budget)
                used = int(metrics["lifetime_tick"])
                achieved = used <= budget
                status_key = "lifetime_tick_budget" if explicit_lifetime_tick_budget is not None else "tick_budget"
                goal_status[status_key] = {
                    "budget_type": "lifetime",
                    "used": used,
                    "budget": budget,
                    "remaining": budget - used,
                    "achieved": achieved,
                }
                if not achieved:
                    reward = 0
                    goal_bonus = 0
            if per_run_tick_budget is not None:
                budget = int(per_run_tick_budget)
                used = int(metrics["tick"])
                achieved = used <= budget
                goal_status["per_run_tick_budget"] = {
                    "used": used,
                    "budget": budget,
                    "remaining": budget - used,
                    "achieved": achieved,
                }
                if not achieved:
                    reward = 0
                    goal_bonus = 0
        completion = goal_completion(goal_status)
        return {
            "reward": int(reward + goal_bonus),
            "metrics": metrics,
            "goal": goal_status,
            "goal_completion": completion,
            "goal_achieved": completion["achieved"],
        }

    def metrics(self) -> dict[str, Any]:
        resource_units = sum(
            int(amount)
            for name, amount in self.state["resources"].items()
            if name != "coins"
        )
        return {
            "tick": self.state["tick"],
            "per_run_tick": self.state["tick"],
            "lifetime_tick": self.state.get("lifetime_tick", self.state["tick"]),
            "run": self.state["run"],
            "retirements": self.state["retirements"],
            "insight": self.state["insight"],
            "storylines_completed": len(self.state["completed_storylines"]),
            "total_element_levels": sum(e["level"] for e in self.state["elements"].values()),
            "total_element_xp": round(sum(e["xp"] for e in self.state["elements"].values()), 3),
            "total_area_clears": sum(self.state["area_clears"].values()),
            "equipment_count": sum(self.state["equipment"].values()),
            "equipment_enhancement_levels": sum(self.state.get("equipment_levels", {}).values()),
            "equipment_spares": sum(self.state.get("equipment_spares", {}).values()),
            "wizards": self.state["wizards"],
            "coins": int(self.state["resources"].get("coins", 0)),
            "resource_units": resource_units,
            "known_spells": len(game.known_spell_ids(self.state, self.data)),
            "known_recipes": len(game.known_recipe_ids(self.state, self.data)),
        }

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
            "tick": self.state["tick"],
            "lifetime_tick": self.state.get("lifetime_tick", self.state["tick"]),
            "command": command,
            "output": output,
            "metrics": self.metrics(),
        })


class ArcaneLabServerSDK:
    """HTTP client SDK for playing through the replay server.

    Use this when the server should be the authoritative game/session owner.
    Commands sent through this client are persisted in the server trajectory.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        game_id: str | None = None,
        new: bool = False,
        label: str | None = None,
        auth_token: str | None = None,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("ARCANE_LAB_SERVER_URL", "http://127.0.0.1:8765")).rstrip("/")
        self.game_id = game_id or os.environ.get("ARCANE_LAB_GAME_ID")
        self.auth_token = auth_token if auth_token is not None else os.environ.get("ARCANE_LAB_AUTH_TOKEN")
        if crit_mode is None:
            crit_mode = os.environ.get("ARCANE_LAB_CRIT_MODE")
        if crit_seed is None:
            crit_seed = os.environ.get("ARCANE_LAB_CRIT_SEED")
        if crit_charge_bonus is None and os.environ.get("ARCANE_LAB_CRIT_CHARGE_BONUS"):
            crit_charge_bonus = float(os.environ["ARCANE_LAB_CRIT_CHARGE_BONUS"])
        if crit_random_chance is None and os.environ.get("ARCANE_LAB_CRIT_RANDOM_CHANCE"):
            crit_random_chance = float(os.environ["ARCANE_LAB_CRIT_RANDOM_CHANCE"])
        if crit_random_bonus is None and os.environ.get("ARCANE_LAB_CRIT_RANDOM_BONUS"):
            crit_random_bonus = float(os.environ["ARCANE_LAB_CRIT_RANDOM_BONUS"])
        self.samples: list[dict[str, Any]] = []
        self.transcript: list[dict[str, Any]] = []
        if not new and not self.game_id:
            self.game_id = self._existing_token_game_id()
        if new or not self.game_id:
            payload: dict[str, Any] = {}
            if label:
                payload["label"] = label
            if crit_mode:
                payload["crit_mode"] = crit_mode
            if crit_seed:
                payload["crit_seed"] = crit_seed
            if crit_charge_bonus is not None:
                payload["crit_charge_bonus"] = crit_charge_bonus
            if crit_random_chance is not None:
                payload["crit_random_chance"] = crit_random_chance
            if crit_random_bonus is not None:
                payload["crit_random_bonus"] = crit_random_bonus
            try:
                game = self._request("POST", "/api/games", payload)
            except RuntimeError as exc:
                existing_game_id = self._existing_token_game_id() if "no remaining new games" in str(exc) else None
                if not existing_game_id:
                    raise
                self.game_id = existing_game_id
                self._sync(self._request("GET", f"/api/games/{urllib.parse.quote(self.game_id)}"))
            else:
                self.game_id = game["summary"]["id"]
                self._sync(game)
        else:
            self._sync(self._request("GET", f"/api/games/{urllib.parse.quote(self.game_id)}"))

    @classmethod
    def from_env(
        cls,
        *,
        game_id: str | None = None,
        new: bool = False,
        label: str | None = None,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> ArcaneLabServerSDK:
        return cls(
            game_id=game_id,
            new=new,
            label=label,
            crit_mode=crit_mode,
            crit_seed=crit_seed,
            crit_charge_bonus=crit_charge_bonus,
            crit_random_chance=crit_random_chance,
            crit_random_bonus=crit_random_bonus,
        )

    def reset(
        self,
        *,
        label: str | None = None,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if label:
            payload["label"] = label
        if crit_mode:
            payload["crit_mode"] = crit_mode
        if crit_seed:
            payload["crit_seed"] = crit_seed
        if crit_charge_bonus is not None:
            payload["crit_charge_bonus"] = crit_charge_bonus
        if crit_random_chance is not None:
            payload["crit_random_chance"] = crit_random_chance
        if crit_random_bonus is not None:
            payload["crit_random_bonus"] = crit_random_bonus
        game = self._request("POST", "/api/games", payload)
        self.game_id = game["summary"]["id"]
        self._sync(game)
        return self.observe()

    def step(self, command: str) -> StepResult:
        game_id = self._quoted_game_id()
        game = self._request("POST", f"/api/games/{game_id}/command", {"command": command})
        self._sync(game)
        entry = game["entry"]
        return StepResult(
            command=entry["command"],
            output=entry["output"],
            observation=game["current"],
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

    def _sync(self, game: dict[str, Any]) -> None:
        summary = game.get("summary") or {}
        if summary.get("id"):
            self.game_id = summary["id"]
        entries = game.get("trajectory", {}).get("entries", [])
        self.transcript = [
            {
                "tick": entry.get("observation", {}).get("tick"),
                "lifetime_tick": entry.get("observation", {}).get("lifetime_tick"),
                "command": entry.get("command"),
                "output": entry.get("output"),
            }
            for entry in entries
        ]
        self.samples = [
            {
                "index": entry.get("index"),
                "tick": entry.get("observation", {}).get("tick"),
                "lifetime_tick": entry.get("observation", {}).get("lifetime_tick"),
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
            headers["X-Arcane-Lab-Token"] = self.auth_token
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
