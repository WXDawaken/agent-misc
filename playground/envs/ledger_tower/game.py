from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "ledger_tower" and ROOT.parent.name == "envs" else ROOT
DATA_PATH = ROOT / "data" / "ledger_tower.json"
DATA_PATH_ENV = "LEDGER_TOWER_DATA_PATH"
DEFAULT_SAVE = PLAYGROUND_ROOT / "saves" / "ledger_tower_state.json"

DIRS = {
    "n": (0, -1),
    "north": (0, -1),
    "up": (0, -1),
    "e": (1, 0),
    "east": (1, 0),
    "right": (1, 0),
    "s": (0, 1),
    "south": (0, 1),
    "down": (0, 1),
    "w": (-1, 0),
    "west": (-1, 0),
    "left": (-1, 0),
}

SYMBOLS = {
    "item": "i",
    "enemy": "m",
    "door": "D",
    "stairs": ">",
    "shop": "$",
    "exit": "X",
}

KEY_SCORE_WEIGHT = 30
MOVE_SCORE_PENALTY = 30


def resolve_data_path(path: str | Path | None = None) -> Path:
    raw_path = path if path is not None else os.environ.get(DATA_PATH_ENV)
    if raw_path is None or str(raw_path).strip() == "":
        return DATA_PATH
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    environment_candidate = ROOT / candidate
    if environment_candidate.exists() or str(candidate).replace("\\", "/").startswith("data/"):
        return environment_candidate
    return PLAYGROUND_ROOT / candidate


def data_path_label(path: str | Path | None) -> str | None:
    if path is None or str(path).strip() == "":
        return None
    resolved = resolve_data_path(path).resolve()
    for root in (ROOT.resolve(), PLAYGROUND_ROOT.resolve()):
        try:
            return str(resolved.relative_to(root)).replace("/", "\\")
        except ValueError:
            continue
    return str(resolved)


def load_data(path: str | Path | None = None) -> dict[str, Any]:
    return json.loads(resolve_data_path(path).read_text(encoding="utf-8"))


def floor_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {floor["id"]: floor for floor in data["floors"]}


def floor_order(data: dict[str, Any]) -> list[str]:
    return [floor["id"] for floor in sorted(data["floors"], key=lambda item: int(item["index"]))]


def resolve_goal_floor_id(target: Any, data: dict[str, Any]) -> str:
    floor_ids = floor_order(data)
    target_text = str(target)
    if target_text in {"$final_floor", "final", "final_floor"}:
        return floor_ids[-1]
    return target_text


def resolve_goal_boss_id(target: Any, data: dict[str, Any]) -> str:
    target_text = str(target)
    if target_text in {"$final_boss", "final", "final_boss"}:
        final_floor = resolve_goal_floor_id("$final_floor", data)
        return f"{final_floor}_boss"
    return target_text


def resolve_numeric_goal_target(target: Any, data: dict[str, Any]) -> int:
    if isinstance(target, dict):
        floor_count = len(floor_order(data))
        by_floor = target.get("by_floor_count")
        if isinstance(by_floor, dict):
            keyed = by_floor.get(str(floor_count))
            if keyed is not None:
                return int(keyed)
        if "default" in target and "base" not in target and "per_floor" not in target:
            return int(target["default"])
        base = int(target.get("base", target.get("default", 0)))
        per_floor = int(target.get("per_floor", 0))
        return base + per_floor * floor_count
    return int(target)


def fresh_state(
    data: dict[str, Any],
    *,
    seed: str | None = None,
    budget: dict[str, Any] | None = None,
    data_path: str | Path | None = None,
) -> dict[str, Any]:
    initial = data["initial_state"]
    metadata = data.get("metadata", {})
    return {
        "env_id": "ledger_tower",
        "version": data["version"],
        "variant": metadata.get("variant") or metadata.get("id", "ledger_tower"),
        "data_path": data_path_label(data_path),
        "seed": seed,
        "floor": initial["floor"],
        "position": list(initial["position"]),
        "hp": int(initial["hp"]),
        "atk": int(initial["atk"]),
        "def": int(initial["def"]),
        "gold": int(initial["gold"]),
        "keys": copy.deepcopy(initial["keys"]),
        "inventory": [],
        "cleared": [],
        "moves": 0,
        "done": False,
        "victory": False,
        "last_action": None,
        "budget": budget or {},
    }


def load_state(path: Path, data: dict[str, Any], force_new: bool = False) -> dict[str, Any]:
    if force_new or not path.exists():
        return fresh_state(data)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("env_id", "ledger_tower")
    payload.setdefault("variant", data.get("metadata", {}).get("variant") or data.get("metadata", {}).get("id", "ledger_tower"))
    payload.setdefault("data_path", data_path_label(os.environ.get(DATA_PATH_ENV)))
    payload.setdefault("keys", {"yellow": 0, "blue": 0, "red": 0})
    payload.setdefault("inventory", [])
    payload.setdefault("cleared", [])
    payload.setdefault("moves", 0)
    payload.setdefault("done", False)
    payload.setdefault("victory", False)
    payload.setdefault("budget", {})
    return payload


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def current_floor(data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return floor_by_id(data)[state["floor"]]


def is_wall(floor: dict[str, Any], x: int, y: int) -> bool:
    if y < 0 or y >= len(floor["grid"]):
        return True
    row = floor["grid"][y]
    if x < 0 or x >= len(row):
        return True
    return row[x] == "#"


def entity_is_cleared(state: dict[str, Any], entity: dict[str, Any]) -> bool:
    return entity["type"] in {"item", "enemy", "door"} and entity["id"] in state["cleared"]


def entity_at(data: dict[str, Any], state: dict[str, Any], floor_id: str, x: int, y: int) -> dict[str, Any] | None:
    floor = floor_by_id(data)[floor_id]
    for entity in floor.get("entities", []):
        if int(entity["x"]) == x and int(entity["y"]) == y and not entity_is_cleared(state, entity):
            return entity
    return None


def entities_on_floor(data: dict[str, Any], state: dict[str, Any], floor_id: str) -> list[dict[str, Any]]:
    floor = floor_by_id(data)[floor_id]
    return [entity for entity in floor.get("entities", []) if not entity_is_cleared(state, entity)]


def apply_effect(state: dict[str, Any], effect: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for stat in ("hp", "atk", "def", "gold"):
        amount = int(effect.get(stat, 0))
        if amount:
            state[stat] = int(state.get(stat, 0)) + amount
            messages.append(f"{stat}+{amount}")
    for key, amount in effect.get("keys", {}).items():
        state["keys"][key] = int(state["keys"].get(key, 0)) + int(amount)
        messages.append(f"{key} key+{int(amount)}")
    return messages


def combat_preview(state: dict[str, Any], enemy: dict[str, Any]) -> dict[str, Any]:
    player_hit = max(0, int(state["atk"]) - int(enemy["def"]))
    enemy_hit = max(0, int(enemy["atk"]) - int(state["def"]))
    if player_hit <= 0:
        return {
            "can_damage": False,
            "survives": False,
            "rounds": None,
            "damage": None,
            "hp_after": int(state["hp"]),
            "enemy_hit": enemy_hit,
            "player_hit": player_hit,
        }
    rounds = math.ceil(int(enemy["hp"]) / player_hit)
    damage = enemy_hit * max(0, rounds - 1)
    hp_after = int(state["hp"]) - damage
    return {
        "can_damage": True,
        "survives": hp_after > 0,
        "rounds": rounds,
        "damage": damage,
        "hp_after": hp_after,
        "enemy_hit": enemy_hit,
        "player_hit": player_hit,
    }


def spend_move(state: dict[str, Any], command: str, output: str, events: list[dict[str, Any]] | None = None) -> None:
    state["moves"] = int(state.get("moves", 0)) + 1
    state["last_action"] = {
        "move": state["moves"],
        "command": command,
        "output": output,
        "events": events or [],
    }


def describe_entity(data: dict[str, Any], entity: dict[str, Any]) -> str:
    kind = entity["type"]
    if kind == "item":
        item = data["items"][entity["item"]]
        return f"{entity['id']}: item {item['name']} at ({entity['x']},{entity['y']})"
    if kind == "enemy":
        enemy = data["enemies"][entity["enemy"]]
        return (
            f"{entity['id']}: enemy {enemy['name']} at ({entity['x']},{entity['y']}) "
            f"hp {enemy['hp']} atk {enemy['atk']} def {enemy['def']} gold {enemy['gold']}"
        )
    if kind == "door":
        return f"{entity['id']}: {entity['key']} door at ({entity['x']},{entity['y']})"
    if kind == "shop":
        return f"{entity['id']}: shop at ({entity['x']},{entity['y']})"
    if kind == "stairs":
        return f"{entity['id']}: stairs to {entity['to_floor']} at ({entity['x']},{entity['y']})"
    if kind == "exit":
        return f"{entity['id']}: exit at ({entity['x']},{entity['y']})"
    return f"{entity['id']}: {kind} at ({entity['x']},{entity['y']})"


def render_floor_map(data: dict[str, Any], state: dict[str, Any], floor_id: str | None = None) -> list[str]:
    floor_id = floor_id or state["floor"]
    floor = floor_by_id(data)[floor_id]
    rows = [list(row) for row in floor["grid"]]
    for entity in entities_on_floor(data, state, floor_id):
        rows[int(entity["y"])][int(entity["x"])] = SYMBOLS.get(entity["type"], "?")
    if floor_id == state["floor"]:
        x, y = state["position"]
        rows[int(y)][int(x)] = "@"
    return ["".join(row) for row in rows]


def entity_public(data: dict[str, Any], state: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "id": entity["id"],
        "type": entity["type"],
        "x": int(entity["x"]),
        "y": int(entity["y"]),
    }
    if entity["type"] == "item":
        payload["item"] = entity["item"]
        payload["name"] = data["items"][entity["item"]]["name"]
        payload["effect"] = copy.deepcopy(data["items"][entity["item"]].get("effect", {}))
    elif entity["type"] == "enemy":
        enemy = copy.deepcopy(data["enemies"][entity["enemy"]])
        payload["enemy"] = entity["enemy"]
        payload["name"] = enemy["name"]
        payload["stats"] = enemy
        payload["preview"] = combat_preview(state, enemy)
    elif entity["type"] == "door":
        payload["key"] = entity["key"]
    elif entity["type"] == "shop":
        shop = data["shops"][entity["shop"]]
        payload["shop"] = entity["shop"]
        payload["name"] = shop["name"]
        payload["offers"] = copy.deepcopy(shop["offers"])
    elif entity["type"] == "stairs":
        payload["to_floor"] = entity["to_floor"]
        payload["to_position"] = list(entity["to_position"])
    elif entity["type"] == "exit":
        payload["requires_item"] = entity.get("requires_item")
    return payload


def budget_observation(state: dict[str, Any]) -> dict[str, Any] | None:
    budget = state.get("budget") or {}
    limit = budget.get("limit")
    soft_stop = budget.get("soft_stop")
    if limit is None and soft_stop is None:
        return None
    used = int(state.get("moves", 0))
    return {
        "metric": "moves",
        "used": used,
        "limit": limit,
        "soft_stop": soft_stop,
        "exceeded": bool(limit is not None and used > int(limit)),
        "soft_stop_exceeded": bool(soft_stop is not None and used > int(soft_stop)),
    }


def metrics(state: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    floor_ids = floor_order(data)
    floor_number = floor_ids.index(state["floor"]) + 1 if state["floor"] in floor_ids else 1
    defeated = [
        entity
        for floor in data["floors"]
        for entity in floor.get("entities", [])
        if entity["type"] == "enemy" and entity["id"] in state["cleared"]
    ]
    opened_doors = [
        entity
        for floor in data["floors"]
        for entity in floor.get("entities", [])
        if entity["type"] == "door" and entity["id"] in state["cleared"]
    ]
    collected = [
        entity
        for floor in data["floors"]
        for entity in floor.get("entities", [])
        if entity["type"] == "item" and entity["id"] in state["cleared"]
    ]
    key_value = int(state["keys"].get("yellow", 0)) + 2 * int(state["keys"].get("blue", 0)) + 3 * int(state["keys"].get("red", 0))
    route_score = (
        (10000 if state.get("victory") else 0)
        + floor_number * 700
        + int(state["hp"]) * 3
        + int(state["gold"]) * 20
        + int(state["atk"]) * 50
        + int(state["def"]) * 50
        + key_value * KEY_SCORE_WEIGHT
        + len(state.get("inventory", [])) * 1000
        - int(state.get("moves", 0)) * MOVE_SCORE_PENALTY
    )
    return {
        "moves": int(state.get("moves", 0)),
        "floor": state["floor"],
        "floor_number": floor_number,
        "hp": int(state["hp"]),
        "atk": int(state["atk"]),
        "def": int(state["def"]),
        "gold": int(state["gold"]),
        "yellow_keys": int(state["keys"].get("yellow", 0)),
        "blue_keys": int(state["keys"].get("blue", 0)),
        "red_keys": int(state["keys"].get("red", 0)),
        "key_value": key_value,
        "artifacts": len(state.get("inventory", [])),
        "defeated_enemies": len(defeated),
        "opened_doors": len(opened_doors),
        "collected_items": len(collected),
        "victory": bool(state.get("victory")),
        "route_score": int(route_score),
    }


def goal_completion(goal_status: dict[str, Any]) -> dict[str, Any]:
    failed = []
    for name, status in goal_status.items():
        achieved = status.get("achieved") if isinstance(status, dict) else bool(status)
        if not achieved:
            failed.append(name)
    total = len(goal_status)
    return {
        "achieved": None if total == 0 else not failed,
        "achieved_count": total - len(failed),
        "total": total,
        "failed": failed,
    }


def score(state: dict[str, Any], data: dict[str, Any], goal: dict[str, Any] | None = None) -> dict[str, Any]:
    current_metrics = metrics(state, data)
    reward = max(0, int(current_metrics["route_score"]))
    goal_status: dict[str, Any] = {}
    if goal:
        if "victory" in goal:
            target = bool(goal["victory"])
            achieved = bool(state.get("victory")) is target
            goal_status["victory"] = {"target": target, "achieved": achieved}
            reward += 5000 if achieved and target else 0
        if "floor" in goal:
            target = resolve_goal_floor_id(goal["floor"], data)
            floor_ids = floor_order(data)
            target_number = floor_ids.index(target) + 1 if target in floor_ids else int(target)
            achieved = int(current_metrics["floor_number"]) >= target_number
            goal_status[f"floor:{target}"] = {
                "current": current_metrics["floor"],
                "target": target,
                "achieved": achieved,
            }
            reward += 1000 if achieved else 0
        if "item" in goal:
            item_id = str(goal["item"])
            achieved = item_id in state.get("inventory", [])
            goal_status[f"item:{item_id}"] = {"owned": achieved, "achieved": achieved}
            reward += 2500 if achieved else 0
        if "boss" in goal:
            boss_id = resolve_goal_boss_id(goal["boss"], data)
            achieved = boss_id in state.get("cleared", [])
            goal_status[f"boss:{boss_id}"] = {"defeated": achieved, "achieved": achieved}
            reward += 2500 if achieved else 0
        for metric_name in ("hp", "gold", "atk", "def", "route_score"):
            key = f"{metric_name}_min"
            if key in goal:
                target = resolve_numeric_goal_target(goal[key], data)
                current = int(current_metrics[metric_name])
                achieved = current >= target
                goal_status[key] = {"current": current, "target": target, "achieved": achieved}
                reward += 1000 if achieved else max(0, current)
        if "moves_max" in goal:
            target = resolve_numeric_goal_target(goal["moves_max"], data)
            used = int(current_metrics["moves"])
            achieved = used <= target
            goal_status["moves_max"] = {
                "used": used,
                "target": target,
                "remaining": target - used,
                "achieved": achieved,
            }
            if not achieved:
                reward = 0
        if "tick_budget" in goal or "lifetime_tick_budget" in goal:
            target = resolve_numeric_goal_target(goal.get("lifetime_tick_budget", goal.get("tick_budget")), data)
            used = int(current_metrics["moves"])
            achieved = used <= target
            goal_status["tick_budget"] = {
                "budget_type": "moves",
                "used": used,
                "budget": target,
                "remaining": target - used,
                "achieved": achieved,
            }
            if not achieved:
                reward = 0
    completion = goal_completion(goal_status)
    return {
        "reward": int(reward),
        "metrics": current_metrics,
        "goal": goal_status,
        "goal_completion": completion,
        "goal_achieved": completion["achieved"],
    }


def status_text(state: dict[str, Any], data: dict[str, Any]) -> str:
    floor = current_floor(data, state)
    x, y = state["position"]
    budget = budget_observation(state)
    budget_line = ""
    if budget:
        budget_line = f" | moves {budget['used']}/{budget.get('limit')}"
        if budget.get("soft_stop") is not None:
            budget_line += f" soft {budget['soft_stop']}"
    return (
        f"{data['metadata']['title']} - {floor['name']} ({state['floor']}) at ({x},{y})\n"
        f"HP {state['hp']} | ATK {state['atk']} | DEF {state['def']} | gold {state['gold']} | "
        f"keys Y{state['keys'].get('yellow', 0)} B{state['keys'].get('blue', 0)} R{state['keys'].get('red', 0)}"
        f"{budget_line}\n"
        f"inventory: {', '.join(state.get('inventory', [])) or 'empty'} | victory: {state.get('victory', False)}"
    )


def observe_state(state: dict[str, Any], data: dict[str, Any], *, include_text: bool = True) -> dict[str, Any]:
    floor = current_floor(data, state)
    floor_entities = [entity_public(data, state, entity) for entity in entities_on_floor(data, state, state["floor"])]
    observation = {
        "env_id": "ledger_tower",
        "done": bool(state.get("done")),
        "moves": int(state.get("moves", 0)),
        "floor": state["floor"],
        "floor_name": floor["name"],
        "position": {"x": int(state["position"][0]), "y": int(state["position"][1])},
        "state": {
            "hp": int(state["hp"]),
            "atk": int(state["atk"]),
            "def": int(state["def"]),
            "gold": int(state["gold"]),
            "keys": copy.deepcopy(state["keys"]),
            "inventory": list(state.get("inventory", [])),
            "victory": bool(state.get("victory")),
        },
        "floor_map": render_floor_map(data, state),
        "floor_entities": floor_entities,
        "known_enemies": copy.deepcopy(data["enemies"]),
        "shops": copy.deepcopy(data["shops"]),
        "available_commands": [
            "status",
            "map",
            "list commands|enemies|items|shops|floors|goals|reference",
            "preview <direction|enemy_id|x y>",
            "move <north|east|south|west> [count]",
            "buy <attack|defense|hp> [count]",
            "save",
            "quit",
        ],
        "last_action": copy.deepcopy(state.get("last_action")),
        "score": score(state, data),
    }
    budget = budget_observation(state)
    if budget:
        observation["budget"] = budget
    if include_text:
        observation["status_text"] = status_text(state, data)
    return observation


def cmd_map(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    floor_ids = floor_order(data)
    requested = args[0] if args else state["floor"]
    if requested == "all":
        chunks = []
        for floor_id in floor_ids:
            floor = floor_by_id(data)[floor_id]
            chunks.append(f"{floor_id} - {floor['name']}")
            chunks.extend(render_floor_map(data, state, floor_id))
        return "\n".join(chunks)
    if requested not in floor_ids:
        return f"Unknown floor {requested!r}. Known floors: {', '.join(floor_ids)}"
    floor = floor_by_id(data)[requested]
    lines = [f"{requested} - {floor['name']}", *render_floor_map(data, state, requested)]
    lines.append("Legend: @ player, i item, m enemy, D door, $ shop, > stairs, X exit, # wall.")
    return "\n".join(lines)


def cmd_list(kind: str, state: dict[str, Any], data: dict[str, Any]) -> str:
    kind = kind.strip().lower() or "commands"
    if kind in {"command", "commands", "help"}:
        return "\n".join([
            "status - show current ledger.",
            "map [floor|all] - show a map.",
            "list enemies|items|shops|floors|goals|reference - inspect public references.",
            "preview <direction|enemy_id|x y> - calculate deterministic fight damage.",
            "move <north|east|south|west> [count] - spend moves to travel, fight, open doors, and collect.",
            "buy <attack|defense|hp> [count] - spend gold at the current shop; each purchase costs one move.",
            "save - write the current state.",
            "quit - end the session.",
        ])
    if kind in {"enemy", "enemies", "monsters"}:
        rows = []
        for enemy_id, enemy in data["enemies"].items():
            preview = combat_preview(state, enemy)
            rows.append(
                f"{enemy_id}: {enemy['name']} hp {enemy['hp']} atk {enemy['atk']} def {enemy['def']} "
                f"gold {enemy['gold']} | damage {preview['damage']} hp_after {preview['hp_after']} "
                f"survives {preview['survives']}"
            )
        return "\n".join(rows)
    if kind in {"item", "items"}:
        return "\n".join(
            f"{item_id}: {item['name']} {item.get('effect', {})}"
            for item_id, item in data["items"].items()
        )
    if kind in {"shop", "shops"}:
        rows = []
        for shop_id, shop in data["shops"].items():
            rows.append(f"{shop_id}: {shop['name']}")
            for offer_id, offer in shop["offers"].items():
                rows.append(f"  {offer_id}: cost {offer['cost']} effect {offer['effect']}")
        return "\n".join(rows)
    if kind in {"floor", "floors"}:
        return "\n".join(f"{floor['id']}: floor {floor['index']} - {floor['name']}" for floor in data["floors"])
    if kind in {"entity", "entities"}:
        return "\n".join(describe_entity(data, entity) for entity in entities_on_floor(data, state, state["floor"]))
    if kind in {"goal", "goals"}:
        return "\n".join([
            "tutorial-clear: reach floor f3 within the move budget.",
            "ledger-clear: defeat f6_boss, collect ledger_core, and exit with enough HP.",
            "high-score: clear the tower while preserving score, HP, gold, and moves.",
        ])
    if kind == "reference":
        return "\n".join([
            "Fight formula: player hits first. Rounds = ceil(enemy_hp / max(1, atk - enemy_def)).",
            "Damage taken = max(0, enemy_atk - def) * (rounds - 1).",
            "A fight is rejected if your attack cannot damage the enemy or projected HP would be 0 or less.",
            "Movement, fights, doors, stairs, item pickups, exits, and purchases each spend moves.",
            "Inspection commands are free: status, map, list, and preview.",
        ])
    return f"Unknown list kind {kind!r}. Try list commands."


def preview_at_entity(data: dict[str, Any], state: dict[str, Any], entity: dict[str, Any]) -> str:
    if entity["type"] != "enemy":
        return describe_entity(data, entity)
    enemy = data["enemies"][entity["enemy"]]
    preview = combat_preview(state, enemy)
    return (
        f"{enemy['name']} at ({entity['x']},{entity['y']}): rounds {preview['rounds']} "
        f"damage {preview['damage']} hp_after {preview['hp_after']} survives {preview['survives']} "
        f"player_hit {preview['player_hit']} enemy_hit {preview['enemy_hit']}"
    )


def cmd_preview(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: preview <direction|enemy_id|x y>."
    floor = current_floor(data, state)
    target = args[0].lower()
    if target in DIRS:
        dx, dy = DIRS[target]
        x, y = int(state["position"][0]) + dx, int(state["position"][1]) + dy
        entity = entity_at(data, state, state["floor"], x, y)
        if not entity:
            return f"No active entity at ({x},{y})."
        return preview_at_entity(data, state, entity)
    if len(args) >= 2 and args[0].lstrip("-").isdigit() and args[1].lstrip("-").isdigit():
        x, y = int(args[0]), int(args[1])
        if is_wall(floor, x, y):
            return f"({x},{y}) is a wall."
        entity = entity_at(data, state, state["floor"], x, y)
        if not entity:
            return f"No active entity at ({x},{y})."
        return preview_at_entity(data, state, entity)
    if target in data["enemies"]:
        enemy = data["enemies"][target]
        preview = combat_preview(state, enemy)
        return (
            f"{enemy['name']}: rounds {preview['rounds']} damage {preview['damage']} "
            f"hp_after {preview['hp_after']} survives {preview['survives']}"
        )
    for entity in entities_on_floor(data, state, state["floor"]):
        if entity["id"].lower() == target:
            return preview_at_entity(data, state, entity)
    return f"Unknown preview target {args[0]!r}."


def move_one(direction: str, state: dict[str, Any], data: dict[str, Any]) -> str:
    direction = direction.lower()
    if state.get("done"):
        return "The run is already done."
    if direction not in DIRS:
        return f"Unknown direction {direction!r}."
    dx, dy = DIRS[direction]
    x, y = int(state["position"][0]) + dx, int(state["position"][1]) + dy
    floor = current_floor(data, state)
    if is_wall(floor, x, y):
        return f"Blocked by a wall at ({x},{y})."
    entity = entity_at(data, state, state["floor"], x, y)
    events: list[dict[str, Any]] = []
    message = f"Moved to ({x},{y})."
    if entity:
        kind = entity["type"]
        if kind == "door":
            key = entity["key"]
            if int(state["keys"].get(key, 0)) <= 0:
                return f"Not enough {key} keys for {entity['id']}."
            state["keys"][key] = int(state["keys"].get(key, 0)) - 1
            state["cleared"].append(entity["id"])
            message = f"Opened {key} door {entity['id']} and moved to ({x},{y})."
            events.append({"type": "door_opened", "entity": entity["id"], "key": key})
        elif kind == "item":
            item = data["items"][entity["item"]]
            effects = apply_effect(state, item.get("effect", {}))
            if item.get("artifact") and entity["item"] not in state["inventory"]:
                state["inventory"].append(entity["item"])
                effects.append(f"artifact:{entity['item']}")
            state["cleared"].append(entity["id"])
            effect_text = ", ".join(effects) if effects else "no stat change"
            message = f"Collected {item['name']} ({effect_text}) at ({x},{y})."
            events.append({"type": "item_collected", "entity": entity["id"], "item": entity["item"]})
        elif kind == "enemy":
            enemy = data["enemies"][entity["enemy"]]
            preview = combat_preview(state, enemy)
            if not preview["can_damage"]:
                return f"Cannot damage {enemy['name']}; need more attack."
            if not preview["survives"]:
                return f"Fight rejected: {enemy['name']} would deal {preview['damage']} damage and leave HP {preview['hp_after']}."
            state["hp"] = int(preview["hp_after"])
            state["gold"] = int(state["gold"]) + int(enemy["gold"])
            state["cleared"].append(entity["id"])
            message = (
                f"Defeated {enemy['name']} for {preview['damage']} damage, "
                f"HP {state['hp']}, gold +{enemy['gold']}."
            )
            events.append({
                "type": "enemy_defeated",
                "entity": entity["id"],
                "enemy": entity["enemy"],
                "damage": preview["damage"],
                "hp_after": preview["hp_after"],
            })
        elif kind == "stairs":
            state["floor"] = entity["to_floor"]
            state["position"] = list(entity["to_position"])
            spend_move(state, f"move {direction}", f"Climbed to {entity['to_floor']}.", [{"type": "stairs", "entity": entity["id"]}])
            return f"Climbed to {entity['to_floor']}."
        elif kind == "shop":
            message = f"Entered {data['shops'][entity['shop']]['name']}. Use buy attack, buy defense, or buy hp."
            events.append({"type": "shop_entered", "entity": entity["id"], "shop": entity["shop"]})
        elif kind == "exit":
            required = entity.get("requires_item")
            if required and required not in state.get("inventory", []):
                return f"The exit requires {required}."
            state["done"] = True
            state["victory"] = True
            message = "Exited Ledger Tower with the ledger balanced."
            events.append({"type": "victory", "entity": entity["id"]})
    state["position"] = [x, y]
    spend_move(state, f"move {direction}", message, events)
    return message


def cmd_move(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: move <north|east|south|west> [count]."
    direction = args[0].lower()
    count = 1
    if len(args) >= 2:
        if not args[1].isdigit():
            return "Move count must be a positive integer."
        count = max(1, int(args[1]))
    outputs = []
    for _ in range(count):
        before = int(state.get("moves", 0))
        output = move_one(direction, state, data)
        outputs.append(output)
        if int(state.get("moves", 0)) == before or state.get("done"):
            break
    return "\n".join(outputs)


def current_shop_entity(state: dict[str, Any], data: dict[str, Any]) -> dict[str, Any] | None:
    x, y = state["position"]
    entity = entity_at(data, state, state["floor"], int(x), int(y))
    return entity if entity and entity["type"] == "shop" else None


def cmd_buy(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if state.get("done"):
        return "The run is already done."
    shop_entity = current_shop_entity(state, data)
    if not shop_entity:
        return "You must stand on a shop to buy."
    if not args:
        return "Usage: buy <attack|defense|hp> [count]."
    offer_id = args[0].lower()
    count = 1
    if len(args) >= 2:
        if not args[1].isdigit():
            return "Buy count must be a positive integer."
        count = max(1, int(args[1]))
    shop = data["shops"][shop_entity["shop"]]
    if offer_id not in shop["offers"]:
        return f"Unknown offer {offer_id!r}. Offers: {', '.join(sorted(shop['offers']))}."
    outputs = []
    for _ in range(count):
        offer = shop["offers"][offer_id]
        cost = int(offer["cost"])
        if int(state["gold"]) < cost:
            outputs.append(f"Not enough gold for {offer_id}; need {cost}, have {state['gold']}.")
            break
        state["gold"] = int(state["gold"]) - cost
        effects = apply_effect(state, offer.get("effect", {}))
        message = f"Bought {offer['name']} for {cost} gold ({', '.join(effects)})."
        spend_move(state, f"buy {offer_id}", message, [{"type": "shop_purchase", "shop": shop_entity["id"], "offer": offer_id}])
        outputs.append(message)
    return "\n".join(outputs)


def execute(command: str, state: dict[str, Any], data: dict[str, Any]) -> tuple[bool, str]:
    raw = command.strip()
    if not raw:
        return True, ""
    parts = raw.split()
    verb = parts[0].lower()
    args = parts[1:]
    if verb in {"help", "?"}:
        return True, cmd_list("commands", state, data)
    if verb in {"status", "observe"}:
        return True, status_text(state, data)
    if verb == "map":
        return True, cmd_map(args, state, data)
    if verb == "list":
        return True, cmd_list(" ".join(args), state, data)
    if verb == "preview":
        return True, cmd_preview(args, state, data)
    if verb in {"move", "go"}:
        return True, cmd_move(args, state, data)
    if verb in DIRS:
        return True, cmd_move([verb, *args], state, data)
    if verb == "buy":
        return True, cmd_buy(args, state, data)
    if verb == "save":
        return True, "Saved."
    if verb in {"quit", "exit"}:
        state["done"] = True
        return False, "Goodbye."
    return True, f"Unknown command: {verb}. Type 'help'."


def run_script(path: Path, state: dict[str, Any], data: dict[str, Any]) -> str:
    output = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            command = raw_line.strip()
            if not command or command.startswith("#"):
                continue
            keep_going, message = execute(command, state, data)
            output.append(f"> {command}")
            if message:
                output.append(message)
            if not keep_going:
                break
    return "\n".join(output)


def repl(state: dict[str, Any], data: dict[str, Any]) -> None:
    print(data["metadata"]["title"])
    print("Type 'help' for commands.")
    while True:
        try:
            command = input("> ")
        except EOFError:
            print()
            break
        keep_going, message = execute(command, state, data)
        if message:
            print(message)
        if not keep_going:
            break


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Ledger Tower text RPG environment.")
    parser.add_argument("--state", type=Path, default=DEFAULT_SAVE, help="Path to a JSON save file.")
    parser.add_argument("--data-path", type=Path, help="Optional alternate Ledger Tower data JSON.")
    parser.add_argument("--script", type=Path, help="Run commands from a script file.")
    parser.add_argument("--new", action="store_true", help="Start from a fresh state.")
    parser.add_argument("--seed", help="Optional deterministic seed label recorded in state.")
    parser.add_argument("--no-save", action="store_true", help="Do not write state after running.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    data_path = resolve_data_path(args.data_path)
    data = load_data(data_path)
    state_path = args.state if args.state.is_absolute() else PLAYGROUND_ROOT / args.state
    state = load_state(state_path, data, args.new)
    if args.new:
        state["data_path"] = data_path_label(data_path)
        state["variant"] = data.get("metadata", {}).get("variant") or data.get("metadata", {}).get("id", "ledger_tower")
    if args.new and args.seed:
        state["seed"] = args.seed
    if args.script:
        script_path = args.script if args.script.is_absolute() else ROOT / args.script
        if not script_path.exists():
            script_path = PLAYGROUND_ROOT / args.script
        print(run_script(script_path, state, data))
    else:
        repl(state, data)
    if not args.no_save:
        save_state(state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
