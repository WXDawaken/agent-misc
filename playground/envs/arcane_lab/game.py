from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "arcane_lab" and ROOT.parent.name == "envs" else ROOT
DATA_PATH = ROOT / "data" / "arcane_lab.json"
DEFAULT_SAVE = PLAYGROUND_ROOT / "saves" / "arcane_lab_state.json"
ACTION_TICKS = {
    "study": 1,
    "cast": 1,
    "explore": 1,
    "transmute": 1,
    "enhance": 0,
    "hire": 1,
}
EQUIPMENT_ENHANCE_BASE = 1.1
DEFAULT_MAX_ENHANCE_LEVEL = 5
CRIT_MODES = {"charge", "random"}
CRIT_MODE_ALIASES = {
    "charge": "charge",
    "deterministic": "charge",
    "random": "random",
    "stochastic": "random",
    "pseudo_random": "random",
    "pseudorandom": "random",
}
DEFAULT_CRIT_SEED = "arcane-lab-default"
DEFAULT_CRIT_CHARGE_BONUS = 0.2
DEFAULT_CRIT_RANDOM_CHANCE = 0.18
DEFAULT_CRIT_RANDOM_BONUS = 0.2


def load_data() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_crit_mode(mode: str | None) -> str:
    if not mode:
        return "charge"
    resolved = CRIT_MODE_ALIASES.get(str(mode).strip().lower())
    if not resolved:
        raise ValueError(f"unknown crit mode: {mode}")
    return resolved


def new_crit_state(
    mode: str | None = None,
    seed: str | None = None,
    *,
    charge_bonus: float | None = None,
    random_chance: float | None = None,
    random_bonus: float | None = None,
) -> dict[str, Any]:
    resolved = resolve_crit_mode(mode)
    return {
        "mode": resolved,
        "charge": 0,
        "max_charge": 3,
        "charge_bonus": float(charge_bonus if charge_bonus is not None else DEFAULT_CRIT_CHARGE_BONUS),
        "random_chance": clamp_fraction(random_chance if random_chance is not None else DEFAULT_CRIT_RANDOM_CHANCE),
        "random_bonus": max(0.0, float(random_bonus if random_bonus is not None else DEFAULT_CRIT_RANDOM_BONUS)),
        "seed": seed or DEFAULT_CRIT_SEED,
        "roll_index": 0,
        "last": None,
    }


def normalize_crit_state(state: dict[str, Any]) -> dict[str, Any]:
    existing = state.get("crit")
    if not isinstance(existing, dict):
        state["crit"] = new_crit_state()
        return state["crit"]
    try:
        mode = resolve_crit_mode(existing.get("mode"))
    except ValueError:
        mode = "charge"
    defaults = new_crit_state(mode, existing.get("seed"))
    for key, value in defaults.items():
        existing.setdefault(key, value)
    existing["mode"] = mode
    existing["charge"] = max(0, min(int(existing.get("charge", 0)), int(existing.get("max_charge", 3))))
    existing["roll_index"] = max(0, int(existing.get("roll_index", 0)))
    state["crit"] = existing
    return existing


def configure_crit_state(
    state: dict[str, Any],
    *,
    mode: str | None = None,
    seed: str | None = None,
    charge_bonus: float | None = None,
    random_chance: float | None = None,
    random_bonus: float | None = None,
    reset: bool = True,
) -> dict[str, Any]:
    current = normalize_crit_state(state)
    resolved = resolve_crit_mode(mode or current.get("mode"))
    next_seed = seed if seed is not None else current.get("seed")
    next_charge_bonus = charge_bonus if charge_bonus is not None else float(current.get("charge_bonus", DEFAULT_CRIT_CHARGE_BONUS))
    next_random_chance = random_chance if random_chance is not None else float(current.get("random_chance", DEFAULT_CRIT_RANDOM_CHANCE))
    next_random_bonus = random_bonus if random_bonus is not None else float(current.get("random_bonus", DEFAULT_CRIT_RANDOM_BONUS))
    if reset:
        state["crit"] = new_crit_state(
            resolved,
            next_seed,
            charge_bonus=next_charge_bonus,
            random_chance=next_random_chance,
            random_bonus=next_random_bonus,
        )
    else:
        current["mode"] = resolved
        if seed is not None:
            current["seed"] = seed
        if charge_bonus is not None:
            current["charge_bonus"] = float(charge_bonus)
        if random_chance is not None:
            current["random_chance"] = clamp_fraction(random_chance)
        if random_bonus is not None:
            current["random_bonus"] = max(0.0, float(random_bonus))
        state["crit"] = current
    return normalize_crit_state(state)


def crit_public_state(state: dict[str, Any], data: dict[str, Any] | None = None) -> dict[str, Any]:
    crit = normalize_crit_state(state)
    base_charge_bonus = float(crit.get("charge_bonus", 0.2))
    base_random_chance = float(crit.get("random_chance", 0.18))
    base_random_bonus = float(crit.get("random_bonus", 0.2))
    if data is None:
        charge_bonus = base_charge_bonus
        random_chance = base_random_chance
        random_bonus = base_random_bonus
        charge_gain = 1
    else:
        charge_bonus = crit_attack_bonus(state, data, "charge")
        random_chance = crit_random_chance(state, data)
        random_bonus = crit_attack_bonus(state, data, "random")
        charge_gain = crit_charge_gain(state, data)
    public = {
        "mode": crit["mode"],
        "charge": int(crit.get("charge", 0)),
        "max_charge": int(crit.get("max_charge", 3)),
        "charge_bonus": charge_bonus,
        "random_chance": random_chance,
        "random_bonus": random_bonus,
        "charge_gain": charge_gain,
        "base_charge_bonus": base_charge_bonus,
        "base_random_chance": base_random_chance,
        "base_random_bonus": base_random_bonus,
        "roll_index": int(crit.get("roll_index", 0)),
        "last": copy.deepcopy(crit.get("last")),
    }
    public["seed_hash"] = hashlib.sha256(str(crit.get("seed", "")).encode("utf-8")).hexdigest()[:12]
    return public


def crit_state_for_new_run(state: dict[str, Any]) -> dict[str, Any]:
    crit = normalize_crit_state(state)
    next_crit = new_crit_state(
        crit.get("mode"),
        crit.get("seed"),
        charge_bonus=float(crit.get("charge_bonus", DEFAULT_CRIT_CHARGE_BONUS)),
        random_chance=float(crit.get("random_chance", DEFAULT_CRIT_RANDOM_CHANCE)),
        random_bonus=float(crit.get("random_bonus", DEFAULT_CRIT_RANDOM_BONUS)),
    )
    next_crit["roll_index"] = int(crit.get("roll_index", 0))
    return next_crit


def fresh_state(
    data: dict[str, Any],
    *,
    crit_mode: str | None = None,
    crit_seed: str | None = None,
    crit_charge_bonus: float | None = None,
    crit_random_chance: float | None = None,
    crit_random_bonus: float | None = None,
) -> dict[str, Any]:
    return {
        "version": data["metadata"]["version"],
        "tick": 0,
        "lifetime_tick": 0,
        "run": 1,
        "retirements": 0,
        "insight": 0,
        "mana": float(data["base"]["max_mana"] * 0.8),
        "hp": float(data["base"]["max_hp"]),
        "resources": copy.deepcopy(data["initial_resources"]),
        "unlocked_elements": list(data["initial_elements"]),
        "elements": {
            element_id: {"level": 1, "xp": 0.0}
            for element_id in data["initial_elements"]
        },
        "unlocked_areas": list(data["initial_areas"]),
        "area_progress": {area_id: 0 for area_id in data["initial_areas"]},
        "area_clears": {area_id: 0 for area_id in data["initial_areas"]},
        "unlocked_spells": [],
        "unlocked_recipes": [],
        "completed_storylines": [],
        "retirement_unlocked": False,
        "wizards": 0,
        "assignments": {},
        "equipment": {},
        "equipment_spares": {},
        "equipment_levels": {},
        "permanent_bonuses": {
            "max_mana": 0,
            "mana_rate": 0,
            "max_hp": 0,
            "attack": 0,
            "defense": 0,
            "study_multiplier": 0,
            "automation_bonus": 0
        },
        "buffs": {},
        "crit": new_crit_state(
            crit_mode,
            crit_seed,
            charge_bonus=crit_charge_bonus,
            random_chance=crit_random_chance,
            random_bonus=crit_random_bonus,
        ),
        "last_action": None,
        "log": []
    }


def normalize_time_state(state: dict[str, Any]) -> dict[str, Any]:
    state["tick"] = int(state.get("tick", 0))
    state["lifetime_tick"] = int(state.get("lifetime_tick", state["tick"]))
    return state


def normalize_equipment_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("equipment", {})
    state.setdefault("equipment_spares", {})
    state.setdefault("equipment_levels", {})
    for key in ("equipment", "equipment_spares", "equipment_levels"):
        state[key] = {
            str(recipe_id): int(amount)
            for recipe_id, amount in dict(state.get(key, {})).items()
            if int(amount) > 0
        }
    return state


def load_state(path: Path, data: dict[str, Any], force_new: bool) -> dict[str, Any]:
    if force_new or not path.exists():
        return fresh_state(data)
    with path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    normalize_time_state(state)
    normalize_equipment_state(state)
    normalize_crit_state(state)
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")


def index_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def resource_text(resources: dict[str, Any]) -> str:
    if not resources:
        return "nothing"
    return ", ".join(f"{name}+{amount}" for name, amount in resources.items())


PERCENT_EFFECT_KEYS = {
    "automation_bonus",
    "crit_bonus",
    "crit_chance",
    "study_multiplier",
}

MULTIPLIER_EFFECT_KEYS = {
    "crit_chance_multiplier",
}


def effect_part_text(key: str, value: Any) -> str:
    if key in PERCENT_EFFECT_KEYS:
        return f"{key}+{float(value) * 100:.0f}%"
    if key in MULTIPLIER_EFFECT_KEYS:
        return f"{key} x{1 + float(value):.2f}"
    return f"{key}+{value}"


def effect_text(effects: dict[str, Any]) -> str:
    if not effects:
        return "none"
    parts = []
    for key, value in effects.items():
        parts.append(effect_part_text(key, value))
    return ", ".join(parts)


def spend_text(resources: dict[str, Any]) -> str:
    if not resources:
        return "nothing"
    return ", ".join(f"{name}-{amount}" for name, amount in resources.items())


def add_log(state: dict[str, Any], message: str) -> None:
    state["log"].append({"tick": state["tick"], "message": message})
    state["log"] = state["log"][-30:]


def equipment_level(state: dict[str, Any], recipe_id: str) -> int:
    normalize_equipment_state(state)
    return int(state.get("equipment_levels", {}).get(recipe_id, 0))


def equipment_multiplier(state: dict[str, Any], recipe_id: str) -> float:
    return EQUIPMENT_ENHANCE_BASE ** equipment_level(state, recipe_id)


def max_enhance_level(recipe: dict[str, Any]) -> int:
    return int(recipe.get("max_enhance", DEFAULT_MAX_ENHANCE_LEVEL))


def enhance_copy_cost(next_level: int) -> int:
    return 2 ** max(0, int(next_level) - 1)


def equipment_bonus(state: dict[str, Any], data: dict[str, Any], key: str) -> float:
    normalize_equipment_state(state)
    recipes = index_by_id(data["recipes"])
    total = 0.0
    for recipe_id, count in state["equipment"].items():
        recipe = recipes.get(recipe_id)
        if recipe:
            total += recipe.get("effects", {}).get(key, 0) * count * equipment_multiplier(state, recipe_id)
    return total


def permanent_bonus(state: dict[str, Any], key: str) -> float:
    return float(state.get("permanent_bonuses", {}).get(key, 0))


def max_mana(state: dict[str, Any], data: dict[str, Any]) -> float:
    return (
        data["base"]["max_mana"]
        + permanent_bonus(state, "max_mana")
        + equipment_bonus(state, data, "max_mana")
        + state.get("insight", 0) * 8
    )


def max_hp(state: dict[str, Any], data: dict[str, Any]) -> float:
    return (
        data["base"]["max_hp"]
        + permanent_bonus(state, "max_hp")
        + equipment_bonus(state, data, "max_hp")
    )


def mana_rate(state: dict[str, Any], data: dict[str, Any]) -> float:
    base = (
        data["base"]["mana_rate"]
        + permanent_bonus(state, "mana_rate")
        + equipment_bonus(state, data, "mana_rate")
    )
    return base * (1 + state.get("insight", 0) * 0.04)


def study_multiplier(state: dict[str, Any], data: dict[str, Any]) -> float:
    return (
        1
        + permanent_bonus(state, "study_multiplier")
        + equipment_bonus(state, data, "study_multiplier")
        + state.get("insight", 0) * 0.05
    )


def automation_bonus(state: dict[str, Any], data: dict[str, Any]) -> float:
    return (
        1
        + permanent_bonus(state, "automation_bonus")
        + equipment_bonus(state, data, "automation_bonus")
    )


def buff_total(state: dict[str, Any], key: str) -> float:
    return sum(float(buff.get(key, 0)) for buff in state.get("buffs", {}).values())


def clamp_fraction(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def crit_bonus_total(state: dict[str, Any], data: dict[str, Any]) -> float:
    return buff_total(state, "crit_bonus") + equipment_bonus(state, data, "crit_bonus")


def crit_random_chance(state: dict[str, Any], data: dict[str, Any]) -> float:
    crit = normalize_crit_state(state)
    base_chance = (
        float(crit.get("random_chance", 0.18))
        + buff_total(state, "crit_chance")
        + equipment_bonus(state, data, "crit_chance")
    )
    multiplier = max(
        0.0,
        1.0
        + buff_total(state, "crit_chance_multiplier")
        + equipment_bonus(state, data, "crit_chance_multiplier"),
    )
    return clamp_fraction(base_chance * multiplier)


def crit_attack_bonus(state: dict[str, Any], data: dict[str, Any], mode: str) -> float:
    crit = normalize_crit_state(state)
    key = "charge_bonus" if mode == "charge" else "random_bonus"
    return max(0.0, float(crit.get(key, 0.2)) + crit_bonus_total(state, data))


def crit_charge_gain(state: dict[str, Any], data: dict[str, Any]) -> int:
    gain = 1 + int(buff_total(state, "crit_charge_gain") + equipment_bonus(state, data, "crit_charge_gain"))
    return max(1, min(gain, int(normalize_crit_state(state).get("max_charge", 3))))


def combat_stats(state: dict[str, Any], data: dict[str, Any]) -> tuple[float, float]:
    ember = state["elements"].get("ember", {}).get("level", 0)
    stone = state["elements"].get("stone", {}).get("level", 0)
    tide = state["elements"].get("tide", {}).get("level", 0)
    gale = state["elements"].get("gale", {}).get("level", 0)
    mind = state["elements"].get("mind", {}).get("level", 0)
    vital = state["elements"].get("vital", {}).get("level", 0)
    attack = (
        data["base"]["attack"]
        + ember * 2.0
        + gale * 1.2
        + mind * 1.5
        + permanent_bonus(state, "attack")
        + equipment_bonus(state, data, "attack")
        + buff_total(state, "attack")
        + buff_total(state, "explore")
    )
    defense = (
        data["base"]["defense"]
        + stone * 2.0
        + tide * 1.2
        + vital * 1.5
        + permanent_bonus(state, "defense")
        + equipment_bonus(state, data, "defense")
        + buff_total(state, "defense")
        + buff_total(state, "explore")
    )
    return attack, defense


def public_boss(area: dict[str, Any]) -> dict[str, Any] | None:
    boss = area.get("boss")
    if not boss:
        return None
    return {
        "name": boss.get("name", "Area Boss"),
        "mechanics": [
            {
                "id": mechanic.get("id"),
                "name": mechanic.get("name", "Mechanic"),
                "hint": mechanic.get("hint", ""),
                "counters": [
                    counter.get("text", "counter")
                    for counter in mechanic.get("counters", [])
                ],
            }
            for mechanic in boss.get("mechanics", [])
        ],
    }


def boss_mechanics_text(area: dict[str, Any]) -> str:
    boss = public_boss(area)
    if not boss:
        return ""
    parts = []
    for mechanic in boss.get("mechanics", []):
        counters = " or ".join(mechanic.get("counters", [])) or "discover a counter"
        hint = mechanic.get("hint", "")
        parts.append(f"{mechanic['name']} ({hint}; counter: {counters})")
    return f"boss {boss['name']}: " + "; ".join(parts)


def _has_any(values: set[str], required: list[str]) -> bool:
    return any(item in values for item in required)


def _has_all(values: set[str], required: list[str]) -> bool:
    return all(item in values for item in required)


def boss_counter_met(
    state: dict[str, Any],
    data: dict[str, Any],
    counter: dict[str, Any],
    crit_event: dict[str, Any] | None = None,
) -> bool:
    active_buffs = set(state.get("buffs", {}).keys())
    equipment = {
        recipe_id
        for recipe_id, count in state.get("equipment", {}).items()
        if int(count) > 0
    }
    known_spells = known_spell_ids(state, data)
    completed = set(state.get("completed_storylines", []))
    checks = [
        ("active_buffs_any", lambda items: _has_any(active_buffs, items)),
        ("active_buffs_all", lambda items: _has_all(active_buffs, items)),
        ("equipment_any", lambda items: _has_any(equipment, items)),
        ("equipment_all", lambda items: _has_all(equipment, items)),
        ("known_spells_any", lambda items: _has_any(known_spells, items)),
        ("known_spells_all", lambda items: _has_all(known_spells, items)),
        ("completed_storylines_any", lambda items: _has_any(completed, items)),
        ("completed_storylines_all", lambda items: _has_all(completed, items)),
    ]
    for key, predicate in checks:
        if key in counter and not predicate(list(counter[key])):
            return False
    if "min_insight" in counter and int(state.get("insight", 0)) < int(counter["min_insight"]):
        return False
    if counter.get("crit_triggered") and not (crit_event or {}).get("triggered"):
        return False
    return True


def unmet_boss_mechanics(
    state: dict[str, Any],
    data: dict[str, Any],
    area: dict[str, Any],
    crit_event: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    boss = area.get("boss") or {}
    failures = []
    for mechanic in boss.get("mechanics", []):
        counters = mechanic.get("counters", [])
        if counters and any(boss_counter_met(state, data, counter, crit_event) for counter in counters):
            continue
        failures.append(mechanic)
    return failures


def unmet_boss_text(failures: list[dict[str, Any]]) -> str:
    parts = []
    for mechanic in failures:
        counters = " or ".join(
            counter.get("text", "counter")
            for counter in mechanic.get("counters", [])
        ) or "discover a counter"
        hint = mechanic.get("hint", "")
        parts.append(f"{mechanic.get('name', 'Mechanic')} ({hint}; try {counters})")
    return "; ".join(parts)


def equipment_summary(state: dict[str, Any], data: dict[str, Any]) -> str:
    normalize_equipment_state(state)
    recipes = index_by_id(data["recipes"])
    rows = []
    recipe_ids = sorted(
        set(state.get("equipment", {}))
        | set(state.get("equipment_spares", {}))
        | set(state.get("equipment_levels", {}))
    )
    for recipe_id in recipe_ids:
        recipe = recipes.get(recipe_id)
        name = recipe.get("name", recipe_id) if recipe else recipe_id
        owned = int(state["equipment"].get(recipe_id, 0))
        level = equipment_level(state, recipe_id)
        spares = int(state["equipment_spares"].get(recipe_id, 0))
        multiplier = equipment_multiplier(state, recipe_id)
        rows.append(f"{recipe_id}:{owned} +{level} x{multiplier:.2f} spares:{spares}")
    return ", ".join(rows) if rows else "none"


def _crit_random_roll(state: dict[str, Any]) -> tuple[int, float]:
    crit = normalize_crit_state(state)
    index = int(crit.get("roll_index", 0))
    seed = str(crit.get("seed") or DEFAULT_CRIT_SEED)
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).hexdigest()
    value = int(digest[:13], 16) / float(16 ** 13)
    crit["roll_index"] = index + 1
    return index, value


def begin_explore_crit(state: dict[str, Any], data: dict[str, Any], attack: float) -> tuple[float, dict[str, Any]]:
    crit = normalize_crit_state(state)
    mode = crit["mode"]
    event: dict[str, Any] = {
        "mode": mode,
        "triggered": False,
        "attack_before": round(float(attack), 3),
        "attack_after": round(float(attack), 3),
        "bonus": 0.0,
    }
    if mode == "charge":
        charge_before = int(crit.get("charge", 0))
        max_charge = int(crit.get("max_charge", 3))
        event.update({
            "charge_before": charge_before,
            "max_charge": max_charge,
            "charge_gain": crit_charge_gain(state, data),
        })
        if charge_before >= max_charge:
            bonus = crit_attack_bonus(state, data, "charge")
            effective_attack = attack * (1 + bonus)
            crit["charge"] = 0
            event.update({
                "triggered": True,
                "bonus": bonus,
                "attack_after": round(float(effective_attack), 3),
                "charge_spent": charge_before,
            })
            return effective_attack, event
        return attack, event
    roll_index, roll = _crit_random_roll(state)
    chance = crit_random_chance(state, data)
    event.update({
        "roll_index": roll_index,
        "roll": round(roll, 6),
        "chance": chance,
    })
    if roll < chance:
        bonus = crit_attack_bonus(state, data, "random")
        effective_attack = attack * (1 + bonus)
        event.update({
            "triggered": True,
            "bonus": bonus,
            "attack_after": round(float(effective_attack), 3),
        })
        return effective_attack, event
    return attack, event


def finish_explore_crit(state: dict[str, Any], data: dict[str, Any], event: dict[str, Any], *, success: bool) -> None:
    crit = normalize_crit_state(state)
    event["success"] = bool(success)
    if event.get("mode") == "charge":
        if success and not event.get("triggered"):
            gain = crit_charge_gain(state, data)
            event["charge_gain"] = gain
            crit["charge"] = min(int(crit.get("max_charge", 3)), int(crit.get("charge", 0)) + gain)
        event["charge_after"] = int(crit.get("charge", 0))
    crit["last"] = copy.deepcopy(event)


def crit_event_text(event: dict[str, Any]) -> str:
    if event.get("mode") == "charge":
        if event.get("triggered"):
            return (
                f"focus crit +{float(event.get('bonus', 0)) * 100:.0f}% atk "
                f"({event['attack_before']:.1f}->{event['attack_after']:.1f}), "
                f"charge {event.get('charge_after', 0)}/{event.get('max_charge', 3)}"
            )
        gain = int(event.get("charge_gain", 1))
        gain_text = f" (+{gain})" if gain != 1 else ""
        return f"focus charge {event.get('charge_after', event.get('charge_before', 0))}/{event.get('max_charge', 3)}{gain_text}"
    outcome = "crit" if event.get("triggered") else "no crit"
    detail = f"roll {float(event.get('roll', 0)):.3f}/{float(event.get('chance', 0)):.3f}"
    if event.get("triggered"):
        detail += f", atk {event['attack_before']:.1f}->{event['attack_after']:.1f}"
    return f"{outcome} ({detail})"


def xp_to_next(level: int) -> int:
    return int(20 * level * level)


def ensure_element(state: dict[str, Any], element_id: str) -> None:
    if element_id not in state["elements"]:
        state["elements"][element_id] = {"level": 1, "xp": 0.0}
    if element_id not in state["unlocked_elements"]:
        state["unlocked_elements"].append(element_id)


def add_element_xp(
    state: dict[str, Any],
    data: dict[str, Any],
    element_id: str,
    amount: float
) -> list[str]:
    ensure_element(state, element_id)
    element = state["elements"][element_id]
    element["xp"] += amount
    messages = []
    while element["xp"] >= xp_to_next(int(element["level"])):
        element["xp"] -= xp_to_next(int(element["level"]))
        element["level"] += 1
        label = data["elements"][element_id]["label"]
        messages.append(f"{label} reached level {element['level']}.")
    return messages


def known_spell_ids(state: dict[str, Any], data: dict[str, Any]) -> set[str]:
    known = set(state.get("unlocked_spells", []))
    completed = set(state.get("completed_storylines", []))
    for spell in data["spells"]:
        requirement = spell.get("requires_storyline")
        element = spell["element"]
        if requirement and requirement not in completed:
            continue
        if element == "universal":
            known.add(spell["id"])
            continue
        if element not in state["unlocked_elements"]:
            continue
        if state["elements"].get(element, {}).get("level", 0) >= spell["level"]:
            known.add(spell["id"])
    return known


def known_recipe_ids(state: dict[str, Any], data: dict[str, Any]) -> set[str]:
    known = set(state.get("unlocked_recipes", []))
    completed = set(state.get("completed_storylines", []))
    for recipe in data["recipes"]:
        requirement = recipe.get("requires_storyline")
        if not requirement or requirement in completed:
            known.add(recipe["id"])
    return known


def can_pay(state: dict[str, Any], costs: dict[str, Any]) -> bool:
    for name, amount in costs.items():
        if name == "mana":
            if state["mana"] < amount:
                return False
        else:
            if state["resources"].get(name, 0) < amount:
                return False
    return True


def pay(state: dict[str, Any], costs: dict[str, Any]) -> None:
    for name, amount in costs.items():
        if name == "mana":
            state["mana"] -= amount
        else:
            state["resources"][name] = state["resources"].get(name, 0) - amount


def gain_resources(
    state: dict[str, Any],
    data: dict[str, Any],
    resources: dict[str, Any]
) -> None:
    for name, amount in resources.items():
        if name == "mana":
            state["mana"] = min(max_mana(state, data), state["mana"] + amount)
        elif name == "hp":
            state["hp"] = min(max_hp(state, data), state["hp"] + amount)
        else:
            state["resources"][name] = state["resources"].get(name, 0) + amount


def decay_buffs(state: dict[str, Any], turns: int = 1) -> None:
    expired = []
    for buff_id, buff in state.get("buffs", {}).items():
        buff["duration"] = int(buff.get("duration", 0)) - turns
        if buff["duration"] <= 0:
            expired.append(buff_id)
    for buff_id in expired:
        state["buffs"].pop(buff_id, None)


def spend_action_time(
    state: dict[str, Any],
    data: dict[str, Any],
    action: str,
    turns: int = 1,
    *,
    decay: bool = True
) -> list[str]:
    if turns <= 0:
        return []
    messages = [f"Action time: {action} took {turns} tick{'s' if turns != 1 else ''}."]
    messages.extend(advance_time(state, data, turns))
    if decay:
        decay_buffs(state, turns)
    state["last_action"] = {
        "action": action,
        "ticks": turns,
        "ended_tick": state["tick"],
        "ended_lifetime_tick": state.get("lifetime_tick", state["tick"]),
    }
    return messages


def apply_spell_effect(
    state: dict[str, Any],
    data: dict[str, Any],
    spell: dict[str, Any],
    automated: bool = False
) -> list[str]:
    effect = spell.get("effect", {})
    messages = []
    if "mana" in effect:
        before = state["mana"]
        gain_resources(state, data, {"mana": effect["mana"]})
        messages.append(f"mana+{state['mana'] - before:.0f}")
    if "resources" in effect:
        gain_resources(state, data, effect["resources"])
        messages.append(resource_text(effect["resources"]))
    if "heal" in effect:
        before = state["hp"]
        gain_resources(state, data, {"hp": effect["heal"]})
        messages.append(f"hp+{state['hp'] - before:.0f}")
    if "buff" in effect:
        buff = copy.deepcopy(effect["buff"])
        buff_id = spell["id"]
        state["buffs"][buff_id] = buff
        parts = [effect_part_text(key, value) for key, value in buff.items() if key != "duration"]
        parts.append(f"{buff.get('duration', 1)} turns")
        messages.append("buff " + ", ".join(parts))
    if "crit_mode_buff" in effect:
        crit_mode = normalize_crit_state(state)["mode"]
        mode_buffs = effect["crit_mode_buff"]
        buff = copy.deepcopy(mode_buffs.get(crit_mode, {}))
        if buff:
            buff_id = spell["id"]
            state["buffs"][buff_id] = buff
            parts = [effect_part_text(key, value) for key, value in buff.items() if key != "duration"]
            parts.append(f"{buff.get('duration', 1)} turns")
            messages.append("buff " + ", ".join(parts))
    if "element_xp_all" in effect:
        amount = float(effect["element_xp_all"]) * study_multiplier(state, data)
        level_messages = []
        for element_id in list(state["unlocked_elements"]):
            level_messages.extend(add_element_xp(state, data, element_id, amount))
        messages.append(f"all elements xp+{amount:.1f}")
        messages.extend(level_messages)
    prefix = "Auto-cast" if automated else "Cast"
    add_log(state, f"{prefix} {spell['name']}: " + "; ".join(messages))
    return messages


def cast_spell(
    state: dict[str, Any],
    data: dict[str, Any],
    spell_id: str,
    automated: bool = False
) -> tuple[bool, str]:
    spells = index_by_id(data["spells"])
    spell = spells.get(spell_id)
    if not spell:
        return False, f"Unknown spell: {spell_id}"
    if spell_id not in known_spell_ids(state, data):
        return False, f"Spell is not known yet: {spell_id}"
    if state["mana"] < spell["mana"]:
        return False, f"Not enough mana for {spell['name']} ({state['mana']:.0f}/{spell['mana']})."
    state["mana"] -= spell["mana"]
    messages = apply_spell_effect(state, data, spell, automated=automated)
    if automated:
        return True, f"auto {spell_id}: " + "; ".join(messages)
    return True, f"{spell['name']} resolved: " + "; ".join(messages)


def advance_time(state: dict[str, Any], data: dict[str, Any], turns: int) -> list[str]:
    messages = []
    spells = index_by_id(data["spells"])
    for _ in range(turns):
        state["tick"] += 1
        state["lifetime_tick"] = int(state.get("lifetime_tick", state["tick"] - 1)) + 1
        before = state["mana"]
        state["mana"] = min(max_mana(state, data), state["mana"] + mana_rate(state, data))
        if int(state["mana"]) != int(before):
            messages.append(f"tick {state['tick']}: mana+{state['mana'] - before:.0f}")
        for spell_id, count in list(state.get("assignments", {}).items()):
            spell = spells.get(spell_id)
            if not spell or count <= 0:
                continue
            casts = max(1, int(math.floor(count * automation_bonus(state, data))))
            for _ in range(casts):
                ok, msg = cast_spell(state, data, spell_id, automated=True)
                if ok:
                    messages.append(f"tick {state['tick']}: {msg}")
                else:
                    break
    return messages


def conditions_met(
    state: dict[str, Any],
    data: dict[str, Any],
    conditions: dict[str, Any]
) -> bool:
    if "total_element_levels" in conditions:
        total = sum(e["level"] for e in state["elements"].values())
        if total < conditions["total_element_levels"]:
            return False
    if "all_initial_elements_level" in conditions:
        target = conditions["all_initial_elements_level"]
        for element_id in data["initial_elements"]:
            if state["elements"].get(element_id, {}).get("level", 0) < target:
                return False
    if "element_levels" in conditions:
        for element_id, level in conditions["element_levels"].items():
            if state["elements"].get(element_id, {}).get("level", 0) < level:
                return False
    if "resources" in conditions:
        for name, amount in conditions["resources"].items():
            if name == "mana":
                if state["mana"] < amount:
                    return False
            elif state["resources"].get(name, 0) < amount:
                return False
    if "area_clears" in conditions:
        for area_id, clears in conditions["area_clears"].items():
            if state["area_clears"].get(area_id, 0) < clears:
                return False
    if "wizards" in conditions and state.get("wizards", 0) < conditions["wizards"]:
        return False
    if "retirements" in conditions and state.get("retirements", 0) < conditions["retirements"]:
        return False
    if "insight" in conditions and state.get("insight", 0) < conditions["insight"]:
        return False
    if "run" in conditions and state.get("run", 1) < conditions["run"]:
        return False
    if "storylines" in conditions:
        completed = set(state.get("completed_storylines", []))
        if not set(conditions["storylines"]).issubset(completed):
            return False
    return True


def storyline_is_visible(
    state: dict[str, Any],
    data: dict[str, Any],
    storyline: dict[str, Any]
) -> bool:
    """Return whether an incomplete storyline should be visible to normal players."""
    conditions = storyline.get("conditions", {})
    completed = set(state.get("completed_storylines", []))
    if storyline["id"] in completed:
        return False
    if "storylines" in conditions and not set(conditions["storylines"]).issubset(completed):
        return False
    if "area_clears" in conditions:
        for area_id in conditions["area_clears"]:
            if area_id not in state.get("unlocked_areas", []):
                return False
    if "element_levels" in conditions:
        for element_id in conditions["element_levels"]:
            if element_id not in state.get("unlocked_elements", []):
                return False
    if "wizards" in conditions and state.get("wizards", 0) <= 0:
        return False
    if "retirements" in conditions and state.get("retirements", 0) <= 0:
        return False
    if "insight" in conditions and state.get("insight", 0) <= 0:
        return False
    if "run" in conditions and state.get("run", 1) <= 1:
        return False
    return True


def goal_progress_entries(
    state: dict[str, Any],
    data: dict[str, Any],
    storyline: dict[str, Any]
) -> list[dict[str, Any]]:
    conditions = storyline.get("conditions", {})
    areas = index_by_id(data["areas"])
    elements = data.get("elements", {})
    entries: list[dict[str, Any]] = []
    if "total_element_levels" in conditions:
        current = sum(e["level"] for e in state["elements"].values())
        target = int(conditions["total_element_levels"])
        entries.append({
            "label": "total element levels",
            "current": current,
            "target": target,
            "achieved": current >= target,
        })
    if "all_initial_elements_level" in conditions:
        target = int(conditions["all_initial_elements_level"])
        current = min(
            int(state["elements"].get(element_id, {}).get("level", 0))
            for element_id in data["initial_elements"]
        )
        entries.append({
            "label": "basic element minimum level",
            "current": current,
            "target": target,
            "achieved": current >= target,
        })
    for element_id, target in conditions.get("element_levels", {}).items():
        current = int(state["elements"].get(element_id, {}).get("level", 0))
        label = elements.get(element_id, {}).get("label", element_id)
        entries.append({
            "label": f"{label} level",
            "current": current,
            "target": int(target),
            "achieved": current >= int(target),
        })
    for name, target in conditions.get("resources", {}).items():
        current = state["mana"] if name == "mana" else state["resources"].get(name, 0)
        entries.append({
            "label": name,
            "current": round(float(current), 3),
            "target": target,
            "achieved": current >= target,
        })
    for area_id, target in conditions.get("area_clears", {}).items():
        current = int(state["area_clears"].get(area_id, 0))
        label = areas.get(area_id, {}).get("name", area_id)
        entries.append({
            "label": f"{label} clears",
            "current": current,
            "target": int(target),
            "achieved": current >= int(target),
        })
    if "wizards" in conditions:
        current = int(state.get("wizards", 0))
        target = int(conditions["wizards"])
        entries.append({
            "label": "wizards",
            "current": current,
            "target": target,
            "achieved": current >= target,
        })
    if "retirements" in conditions:
        current = int(state.get("retirements", 0))
        target = int(conditions["retirements"])
        entries.append({
            "label": "retirements",
            "current": current,
            "target": target,
            "achieved": current >= target,
        })
    if "insight" in conditions:
        current = int(state.get("insight", 0))
        target = int(conditions["insight"])
        entries.append({
            "label": "insight",
            "current": current,
            "target": target,
            "achieved": current >= target,
        })
    if "run" in conditions:
        current = int(state.get("run", 1))
        target = int(conditions["run"])
        entries.append({
            "label": "run",
            "current": current,
            "target": target,
            "achieved": current >= target,
        })
    for storyline_id in conditions.get("storylines", []):
        achieved = storyline_id in state.get("completed_storylines", [])
        entries.append({
            "label": f"storyline {storyline_id}",
            "current": 1 if achieved else 0,
            "target": 1,
            "achieved": achieved,
        })
    return entries


def visible_storyline_summaries(
    state: dict[str, Any],
    data: dict[str, Any],
    *,
    limit: int | None = None
) -> list[dict[str, Any]]:
    summaries = []
    for storyline in data["storylines"]:
        if not storyline_is_visible(state, data, storyline):
            continue
        summaries.append({
            "id": storyline["id"],
            "name": storyline["name"],
            "description": storyline["description"],
            "progress": goal_progress_entries(state, data, storyline),
        })
        if limit is not None and len(summaries) >= limit:
            break
    return summaries


def goal_progress_text(progress: list[dict[str, Any]]) -> str:
    if not progress:
        return "discovery"
    parts = []
    for item in progress:
        marker = "done" if item.get("achieved") else "todo"
        parts.append(f"{item['label']} {item['current']}/{item['target']} {marker}")
    return "; ".join(parts)


def apply_story_rewards(
    state: dict[str, Any],
    data: dict[str, Any],
    rewards: dict[str, Any]
) -> list[str]:
    messages = []
    if "resources" in rewards:
        gain_resources(state, data, rewards["resources"])
        messages.append(resource_text(rewards["resources"]))
    if "permanent_bonuses" in rewards:
        for key, amount in rewards["permanent_bonuses"].items():
            state["permanent_bonuses"][key] = state["permanent_bonuses"].get(key, 0) + amount
        messages.append("permanent " + resource_text(rewards["permanent_bonuses"]))
    if "wizards" in rewards:
        state["wizards"] += rewards["wizards"]
        messages.append(f"wizards+{rewards['wizards']}")
    for recipe_id in rewards.get("unlock_recipes", []):
        if recipe_id not in state["unlocked_recipes"]:
            state["unlocked_recipes"].append(recipe_id)
        messages.append(f"recipe:{recipe_id}")
    for spell_id in rewards.get("unlock_spells", []):
        if spell_id not in state["unlocked_spells"]:
            state["unlocked_spells"].append(spell_id)
        messages.append(f"spell:{spell_id}")
    for area_id in rewards.get("unlock_areas", []):
        unlock_area(state, area_id)
        messages.append(f"area:{area_id}")
    for element_id in rewards.get("unlock_elements", []):
        ensure_element(state, element_id)
        messages.append(f"element:{element_id}")
    if rewards.get("unlock_retirement"):
        state["retirement_unlocked"] = True
        messages.append("retirement unlocked")
    state["hp"] = min(state["hp"], max_hp(state, data))
    state["mana"] = min(state["mana"], max_mana(state, data))
    return messages


def check_storylines(state: dict[str, Any], data: dict[str, Any]) -> list[str]:
    messages = []
    changed = True
    while changed:
        changed = False
        completed = set(state.get("completed_storylines", []))
        for storyline in data["storylines"]:
            if storyline["id"] in completed:
                continue
            if conditions_met(state, data, storyline.get("conditions", {})):
                state["completed_storylines"].append(storyline["id"])
                rewards = apply_story_rewards(state, data, storyline.get("rewards", {}))
                message = f"Storyline complete: {storyline['name']} ({'; '.join(rewards)})"
                messages.append(message)
                add_log(state, message)
                changed = True
                break
    return messages


def unlock_area(state: dict[str, Any], area_id: str) -> None:
    if area_id not in state["unlocked_areas"]:
        state["unlocked_areas"].append(area_id)
    state["area_progress"].setdefault(area_id, 0)
    state["area_clears"].setdefault(area_id, 0)


def cmd_status(state: dict[str, Any], data: dict[str, Any]) -> str:
    attack, defense = combat_stats(state, data)
    crit = crit_public_state(state, data)
    if crit["mode"] == "charge":
        crit_text = (
            f"charge {crit['charge']}/{crit['max_charge']} "
            f"(+{crit['charge_bonus'] * 100:.0f}% atk at full, +{crit['charge_gain']} charge/success)"
        )
    else:
        crit_text = (
            f"random {crit['random_chance'] * 100:.0f}% "
            f"(+{crit['random_bonus'] * 100:.0f}% atk, roll {crit['roll_index']})"
        )
    elements = ", ".join(
        f"{element_id}:{entry['level']}({entry['xp']:.0f}/{xp_to_next(entry['level'])})"
        for element_id, entry in sorted(state["elements"].items())
    )
    resources = ", ".join(
        f"{name}:{amount}" for name, amount in sorted(state["resources"].items())
    )
    buffs = ", ".join(
        f"{name}[{buff.get('duration', 0)}]"
        for name, buff in state.get("buffs", {}).items()
    ) or "none"
    assignments = ", ".join(
        f"{spell_id}:{count}"
        for spell_id, count in sorted(state.get("assignments", {}).items())
    ) or "none"
    last_action = state.get("last_action")
    if last_action:
        tick_unit = "ticks" if last_action["ticks"] != 1 else "tick"
        last_action_text = f"{last_action['action']} ({last_action['ticks']} {tick_unit}, ended {last_action['ended_tick']})"
        if last_action.get("payloads"):
            last_action_text += " [" + ", ".join(last_action["payloads"]) + "]"
    else:
        last_action_text = "none"
    return (
        f"Run {state['run']} tick {state['tick']} | lifetime {state.get('lifetime_tick', state['tick'])} | "
        f"mana {state['mana']:.0f}/{max_mana(state, data):.0f} "
        f"(+{mana_rate(state, data):.1f}/tick), hp {state['hp']:.0f}/{max_hp(state, data):.0f}, "
        f"atk {attack:.1f}, def {defense:.1f}, wizards {state['wizards']}, insight {state['insight']}\n"
        f"Elements: {elements}\n"
        f"Resources: {resources}\n"
        f"Equipment: {equipment_summary(state, data)}\n"
        f"Areas: {', '.join(state['unlocked_areas'])}\n"
        f"Assignments: {assignments}\n"
        f"Buffs: {buffs}\n"
        f"Crit: {crit_text}\n"
        f"Last action: {last_action_text}"
    )


def cmd_study(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: study <element> [turns]"
    element_id = args[0]
    if element_id not in state["unlocked_elements"]:
        return f"Element is not unlocked: {element_id}"
    turns = int(args[1]) if len(args) > 1 else 1
    messages = []
    for _ in range(max(0, turns)):
        messages.extend(spend_action_time(state, data, f"study {element_id}", ACTION_TICKS["study"]))
        level = state["elements"][element_id]["level"]
        cost = data["base"]["study_cost"] + 2 * level
        if state["mana"] < cost:
            messages.append(f"Stopped: not enough mana to study {element_id} ({state['mana']:.0f}/{cost}).")
            break
        state["mana"] -= cost
        gain = data["base"]["study_xp"] * study_multiplier(state, data)
        level_messages = add_element_xp(state, data, element_id, gain)
        messages.append(f"Studied {element_id}: mana-{cost}, xp+{gain:.1f}.")
        messages.extend(level_messages)
    messages.extend(check_storylines(state, data))
    return "\n".join(messages) if messages else "No study turns run."


def cmd_cast(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: cast <spell>"
    spell_id = args[0]
    spells = index_by_id(data["spells"])
    if spell_id not in spells:
        return f"Unknown spell: {spell_id}"
    if spell_id not in known_spell_ids(state, data):
        return f"Spell is not known yet: {spell_id}"
    messages = spend_action_time(state, data, f"cast {spell_id}", ACTION_TICKS["cast"])
    ok, message = cast_spell(state, data, args[0])
    messages.append(message)
    if ok:
        messages.extend(check_storylines(state, data))
    return "\n".join(messages)


def parse_batch_payloads(
    batch_verb: str,
    args: list[str]
) -> tuple[list[tuple[str, int, int]], str | None]:
    parsed = []
    seen = set()
    for index, raw in enumerate(args):
        payload = raw
        priority = index
        if "@" in raw:
            payload, _, priority_text = raw.rpartition("@")
            if not payload or not priority_text:
                return [], f"Invalid batch payload: {raw}"
            try:
                priority = int(priority_text)
            except ValueError:
                return [], f"Invalid priority in batch payload: {raw}"
        if payload in seen:
            hint = (
                f" Use transmute {payload} <count> for repeated copies."
                if batch_verb == "transmute"
                else " Repeat casts must be issued as separate actions."
            )
            return [], f"Duplicate batch payload is not allowed: {payload}.{hint}"
        seen.add(payload)
        parsed.append((payload, priority, index))
    parsed.sort(key=lambda item: (item[1], item[2]))
    return parsed, None


def apply_transmute_once(
    state: dict[str, Any],
    data: dict[str, Any],
    recipe_id: str
) -> tuple[bool, str]:
    recipes = index_by_id(data["recipes"])
    recipe = recipes.get(recipe_id)
    if not recipe:
        return False, "unknown recipe"
    if recipe_id not in known_recipe_ids(state, data):
        return False, "recipe is not known yet"
    owned = state["equipment"].get(recipe_id, 0)
    if not can_pay(state, recipe["cost"]):
        return False, f"cannot pay for {recipe['name']} ({spend_text(recipe['cost'])})"
    pay(state, recipe["cost"])
    max_owned = int(recipe.get("max_owned", 1))
    if owned < max_owned:
        state["equipment"][recipe_id] = owned + 1
        result = f"transmuted {recipe['name']} ({spend_text(recipe['cost'])})"
    else:
        spares = state.setdefault("equipment_spares", {}).get(recipe_id, 0) + 1
        state["equipment_spares"][recipe_id] = spares
        result = f"transmuted spare +0 {recipe['name']} ({spend_text(recipe['cost'])}); spares {spares}"
    state["mana"] = min(state["mana"], max_mana(state, data))
    state["hp"] = min(max_hp(state, data), state["hp"] + recipe.get("effects", {}).get("max_hp", 0))
    return True, result


def apply_transmute_once_preview(
    state: dict[str, Any],
    data: dict[str, Any],
    recipe_id: str
) -> tuple[bool, str]:
    recipes = index_by_id(data["recipes"])
    recipe = recipes.get(recipe_id)
    if not recipe:
        return False, f"unknown recipe: {recipe_id}"
    if recipe_id not in known_recipe_ids(state, data):
        return False, f"recipe is not known yet: {recipe_id}"
    owned = state["equipment"].get(recipe_id, 0)
    if not can_pay(state, recipe["cost"]):
        return False, f"cannot pay for {recipe['name']} ({spend_text(recipe['cost'])})"
    return True, "ok"


def cmd_batch(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if len(args) < 2:
        return "Usage: batch <cast|transmute> <payload[@priority] ...>"
    batch_verb = args[0]
    if batch_verb not in {"cast", "transmute"}:
        return "Batch supports only cast and transmute."
    payloads, error = parse_batch_payloads(batch_verb, args[1:])
    if error:
        return error
    messages = spend_action_time(
        state,
        data,
        f"batch {batch_verb}",
        ACTION_TICKS[batch_verb],
    )
    state["last_action"]["payloads"] = [payload for payload, _, _ in payloads]
    for payload, priority, original_index in payloads:
        label = f"{payload}@{priority}" if priority != original_index else payload
        if batch_verb == "cast":
            ok, message = cast_spell(state, data, payload)
        else:
            ok, message = apply_transmute_once(state, data, payload)
        status = "ok" if ok else "fail"
        messages.append(f"{status} {label}: {message}")
    messages.extend(check_storylines(state, data))
    return "\n".join(messages)


def cmd_tick(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    turns = int(args[0]) if args else 1
    messages = advance_time(state, data, max(0, turns))
    decay_buffs(state, max(0, turns))
    if turns > 0:
        state["last_action"] = {
            "action": "wait",
            "ticks": turns,
            "ended_tick": state["tick"],
            "ended_lifetime_tick": state.get("lifetime_tick", state["tick"]),
        }
    messages.extend(check_storylines(state, data))
    return "\n".join(messages) if messages else f"Advanced {turns} ticks."


def cmd_assign(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if len(args) < 2:
        return "Usage: assign <spell> <count> (use 0 to stop automation)"
    spell_id = args[0]
    count = int(args[1])
    spells = index_by_id(data["spells"])
    if spell_id not in spells:
        return f"Unknown spell: {spell_id}"
    if spell_id not in known_spell_ids(state, data):
        return f"Spell is not known yet: {spell_id}"
    if not spells[spell_id].get("automation", False):
        return f"Spell cannot be automated: {spell_id}"
    current = dict(state.get("assignments", {}))
    if count <= 0:
        current.pop(spell_id, None)
    else:
        current[spell_id] = count
    if sum(current.values()) > state.get("wizards", 0):
        return f"Not enough wizards. Assigned {sum(current.values())}, available {state.get('wizards', 0)}."
    state["assignments"] = current
    return "Assignments: " + (", ".join(f"{k}:{v}" for k, v in sorted(current.items())) or "none")


def cmd_unassign(args: list[str], state: dict[str, Any]) -> str:
    if not args:
        state["assignments"] = {}
        return "Assignments: none"
    current = dict(state.get("assignments", {}))
    missing = []
    for spell_id in args:
        if spell_id in current:
            current.pop(spell_id, None)
        else:
            missing.append(spell_id)
    state["assignments"] = current
    result = "Assignments: " + (", ".join(f"{k}:{v}" for k, v in sorted(current.items())) or "none")
    if missing:
        result += "\nNot assigned: " + ", ".join(missing)
    return result


def cmd_hire(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    count = int(args[0]) if args else 1
    messages = []
    for _ in range(max(0, count)):
        cost = int(data["base"]["wizard_cost"] + 25 * (state["wizards"] ** 1.35))
        if state["resources"].get("coins", 0) < cost:
            messages.append(f"Stopped: not enough coins for wizard ({state['resources'].get('coins', 0)}/{cost}).")
            break
        messages.extend(spend_action_time(state, data, "hire wizard", ACTION_TICKS["hire"]))
        state["resources"]["coins"] -= cost
        state["wizards"] += 1
        messages.append(f"Hired wizard {state['wizards']}: coins-{cost}.")
    messages.extend(check_storylines(state, data))
    return "\n".join(messages) if messages else "No wizards hired."


def cmd_explore(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: explore <area> [times]"
    area_id = args[0]
    times = int(args[1]) if len(args) > 1 else 1
    areas = index_by_id(data["areas"])
    area = areas.get(area_id)
    if not area:
        return f"Unknown area: {area_id}"
    if area_id not in state["unlocked_areas"]:
        return f"Area is not unlocked: {area_id}"
    messages = []
    for _ in range(max(0, times)):
        messages.extend(spend_action_time(
            state,
            data,
            f"explore {area_id}",
            ACTION_TICKS["explore"],
            decay=False
        ))
        attack, defense = combat_stats(state, data)
        effective_attack, crit_event = begin_explore_crit(state, data, attack)
        attack_required = float(area["requires_attack"])
        defense_required = float(area["requires_defense"])
        boss_attempt = state["area_progress"].get(area_id, 0) + 1 >= area["clears_required"]
        mechanic_failures = unmet_boss_mechanics(state, data, area, crit_event) if boss_attempt else []
        if mechanic_failures:
            pressure = sum(float(mechanic.get("damage", 4)) for mechanic in mechanic_failures)
            attack_required += pressure
            defense_required += pressure
        success = effective_attack >= attack_required and defense >= defense_required
        finish_explore_crit(state, data, crit_event, success=success)
        crit_text = crit_event_text(crit_event)
        if success:
            gain_resources(state, data, area["rewards"])
            state["area_progress"][area_id] = state["area_progress"].get(area_id, 0) + 1
            progress = state["area_progress"][area_id]
            needed = area["clears_required"]
            mechanic_text = ""
            if mechanic_failures:
                mechanic_text = f" Boss pressure overpowered despite missing counters: {unmet_boss_text(mechanic_failures)}."
            messages.append(
                f"Explored {area['name']}: success ({progress}/{needed}), "
                f"{resource_text(area['rewards'])}. {crit_text}.{mechanic_text}"
            )
            if progress >= needed:
                state["area_progress"][area_id] = 0
                state["area_clears"][area_id] = state["area_clears"].get(area_id, 0) + 1
                for next_area in area.get("unlock_areas", []):
                    unlock_area(state, next_area)
                boss = area.get("boss")
                suffix = f"; defeated {boss['name']}" if boss else ""
                messages.append(f"Cleared {area['name']} #{state['area_clears'][area_id]}{suffix}.")
        else:
            gap = max(attack_required - effective_attack, 0) + max(defense_required - defense, 0)
            mechanic_damage = sum(int(mechanic.get("damage", 4)) for mechanic in mechanic_failures)
            damage = max(3, math.ceil(gap * 3) + mechanic_damage)
            state["hp"] -= damage
            mechanic_text = ""
            if mechanic_failures:
                mechanic_text = f" Boss pressure: missing counters raised the final clear need; {unmet_boss_text(mechanic_failures)}."
            messages.append(
                f"Explored {area['name']}: failed, hp-{damage} "
                f"(need atk {attack_required:.0f}/def {defense_required:.0f}, "
                f"had atk {effective_attack:.1f}/def {defense:.1f}).{mechanic_text} {crit_text}."
            )
            if state["hp"] <= 0:
                state["hp"] = max_hp(state, data)
                state["mana"] = min(state["mana"], max_mana(state, data) * 0.5)
                messages.append("You retreated and recovered at the lab; mana was capped to half.")
        decay_buffs(state, 1)
    messages.extend(check_storylines(state, data))
    return "\n".join(messages) if messages else "No exploration attempted."


def cmd_transmute(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: transmute <recipe> [count]"
    recipe_id = args[0]
    count = int(args[1]) if len(args) > 1 else 1
    recipes = index_by_id(data["recipes"])
    recipe = recipes.get(recipe_id)
    if not recipe:
        return f"Unknown recipe: {recipe_id}"
    if recipe_id not in known_recipe_ids(state, data):
        return f"Recipe is not known yet: {recipe_id}"
    messages = []
    for _ in range(max(0, count)):
        ok, preview = apply_transmute_once_preview(state, data, recipe_id)
        if not ok:
            messages.append("Stopped: " + preview + ".")
            break
        messages.extend(spend_action_time(state, data, f"transmute {recipe_id}", ACTION_TICKS["transmute"]))
        ok, result = apply_transmute_once(state, data, recipe_id)
        messages.append(result + ".")
    messages.extend(check_storylines(state, data))
    return "\n".join(messages) if messages else "No transmutation performed."


def cmd_enhance(args: list[str], state: dict[str, Any], data: dict[str, Any]) -> str:
    if not args:
        return "Usage: enhance <recipe> [levels]"
    recipe_id = args[0]
    levels = int(args[1]) if len(args) > 1 else 1
    recipes = index_by_id(data["recipes"])
    recipe = recipes.get(recipe_id)
    if not recipe:
        return f"Unknown recipe: {recipe_id}"
    if recipe_id not in known_recipe_ids(state, data):
        return f"Recipe is not known yet: {recipe_id}"
    normalize_equipment_state(state)
    owned = int(state["equipment"].get(recipe_id, 0))
    if owned <= 0:
        return f"No equipped {recipe['name']} to enhance."

    messages = []
    for _ in range(max(0, levels)):
        current = equipment_level(state, recipe_id)
        next_level = current + 1
        max_level = max_enhance_level(recipe)
        if current >= max_level:
            messages.append(f"Stopped: {recipe['name']} is already +{current} (max +{max_level}).")
            break
        needed = enhance_copy_cost(next_level)
        spares = int(state["equipment_spares"].get(recipe_id, 0))
        if spares < needed:
            copy_word = "copy" if needed == 1 else "copies"
            messages.append(
                f"Stopped: {recipe['name']} +{next_level} needs {needed} spare +0 "
                f"{copy_word} ({spares}/{needed})."
            )
            break
        messages.extend(spend_action_time(state, data, f"enhance {recipe_id}", ACTION_TICKS["enhance"]))
        state["equipment_spares"][recipe_id] = spares - needed
        if state["equipment_spares"][recipe_id] <= 0:
            state["equipment_spares"].pop(recipe_id, None)
        state["equipment_levels"][recipe_id] = next_level
        multiplier = equipment_multiplier(state, recipe_id)
        copy_word = "copy" if needed == 1 else "copies"
        messages.append(
            f"Enhanced {recipe['name']} to +{next_level}: consumed {needed} spare +0 "
            f"{copy_word}; effects x{multiplier:.3f}."
        )
        state["mana"] = min(state["mana"], max_mana(state, data))
        state["hp"] = min(state["hp"], max_hp(state, data))
    messages.extend(check_storylines(state, data))
    return "\n".join(messages) if messages else "No enhancement performed."


def cmd_retire(state: dict[str, Any], data: dict[str, Any]) -> str:
    if not state.get("retirement_unlocked"):
        return "Retirement is not unlocked yet."
    total_levels = sum(e["level"] for e in state["elements"].values())
    clears = sum(state["area_clears"].values())
    gained = max(1, total_levels // 5 + clears + len(state["completed_storylines"]) // 3)
    preserved = {
        "retirements": state["retirements"] + 1,
        "insight": state["insight"] + gained,
        "completed_storylines": list(state["completed_storylines"]),
        "unlocked_areas": list(state.get("unlocked_areas", [])),
        "unlocked_elements": list(state.get("unlocked_elements", [])),
        "unlocked_spells": list(state["unlocked_spells"]),
        "unlocked_recipes": list(state["unlocked_recipes"]),
        "retirement_unlocked": True,
        "permanent_bonuses": copy.deepcopy(state["permanent_bonuses"]),
        "crit": crit_state_for_new_run(state),
        "lifetime_tick": int(state.get("lifetime_tick", state["tick"])),
    }
    new_state = fresh_state(data)
    new_state.update(preserved)
    new_state["run"] = state["run"] + 1
    for area_id in list(new_state.get("unlocked_areas", [])):
        unlock_area(new_state, area_id)
    for element_id in list(new_state.get("unlocked_elements", [])):
        ensure_element(new_state, element_id)
    for storyline in data["storylines"]:
        if storyline["id"] in new_state["completed_storylines"]:
            rewards = storyline.get("rewards", {})
            for area_id in rewards.get("unlock_areas", []):
                unlock_area(new_state, area_id)
            for element_id in rewards.get("unlock_elements", []):
                ensure_element(new_state, element_id)
    state.clear()
    state.update(new_state)
    messages = [f"Retired run. Gained insight+{gained}; total insight {state['insight']}."]
    messages.extend(check_storylines(state, data))
    return "\n".join(messages)


def reference_text(state: dict[str, Any], data: dict[str, Any]) -> str:
    crit = crit_public_state(state, data)
    known = known_spell_ids(state, data)
    buff_rows = []
    for spell in data["spells"]:
        if spell["id"] not in known:
            continue
        effect = spell.get("effect", {})
        buff = effect.get("buff")
        if buff:
            parts = [effect_part_text(key, value) for key, value in buff.items() if key != "duration"]
            if parts:
                parts.append(f"duration {buff.get('duration', 0)}")
                buff_rows.append(f"- {spell['id']}: mana {spell['mana']}, " + ", ".join(parts))
        crit_mode_buff = effect.get("crit_mode_buff", {})
        active_crit_buff = crit_mode_buff.get(crit["mode"], {})
        if active_crit_buff:
            parts = [
                effect_part_text(key, value)
                for key, value in active_crit_buff.items()
                if key != "duration"
            ]
            if parts:
                parts.append(f"duration {active_crit_buff.get('duration', 0)}")
                buff_rows.append(f"- {spell['id']}: mana {spell['mana']}, " + ", ".join(parts))
    if not buff_rows:
        buff_rows.append("- No known temporary buff spells yet.")

    return "\n".join(
        [
            "Reference commands:",
            "- list actions: command tick costs and batch action costs",
            "- list buffs: active buffs and remaining durations",
            "- list crit: active crit mode and effective crit values",
            "- list areas: combat requirements, progress, and visible boss hints",
            "- list goals: visible storyline goals and progress hints",
            "",
            "Known temporary buff reference:",
            *buff_rows,
            "",
            "Batching reference:",
            "- batch cast and batch transmute each spend 1 tick total.",
            "- Payloads resolve by explicit @priority first, then command order.",
            "- Duplicate payload ids in one batch are rejected; use transmute <recipe> [count] for repeated copies.",
            "",
            "Route reference:",
            "- Keep long routes as compact command files with checkpoints or pivot points.",
            "- Practice offline until failed commands are removed, then submit one clean official server route.",
            "- Avoid open-ended grinding once a concrete route can finish the known goal.",
        ]
    )


def cmd_list(kind: str, state: dict[str, Any], data: dict[str, Any]) -> str:
    parts = kind.split()
    primary = parts[0].lower() if parts else ""
    debug = len(parts) > 1 and parts[1].lower() == "debug"
    if primary == "goals_debug":
        primary = "goals"
        debug = True
    if primary == "spells":
        known = known_spell_ids(state, data)
        rows = []
        for spell in data["spells"]:
            if spell["id"] in known:
                auto = "auto" if spell.get("automation") else "manual"
                rows.append(f"{spell['id']}: {spell['name']} [{auto}] mana {spell['mana']} - {spell['description']}")
        return "\n".join(rows) if rows else "No known spells."
    if primary == "recipes":
        known = known_recipe_ids(state, data)
        rows = []
        for recipe in data["recipes"]:
            if recipe["id"] in known:
                recipe_id = recipe["id"]
                normalize_equipment_state(state)
                owned = state["equipment"].get(recipe_id, 0)
                level = equipment_level(state, recipe_id)
                spares = state["equipment_spares"].get(recipe_id, 0)
                next_level = level + 1
                max_level = max_enhance_level(recipe)
                if not owned:
                    next_text = "own first"
                elif owned < int(recipe.get("max_owned", 1)):
                    next_text = f"own {int(recipe.get('max_owned', 1)) - owned} more before spares"
                elif level < max_level:
                    next_text = f"+{next_level} needs {enhance_copy_cost(next_level)} spare +0"
                else:
                    next_text = "max"
                cost = ", ".join(f"{k}:{v}" for k, v in recipe["cost"].items())
                effects = effect_text(recipe.get("effects", {}))
                rows.append(
                    f"{recipe_id}: {recipe['name']} owned {owned}/{recipe['max_owned']} "
                    f"+{level} x{equipment_multiplier(state, recipe_id):.2f} spares {spares} "
                    f"next {next_text} cost {cost} | effects {effects} - {recipe['description']}"
                )
        return "\n".join(rows) if rows else "No known recipes."
    if primary == "areas":
        areas = index_by_id(data["areas"])
        attack, defense = combat_stats(state, data)
        rows = []
        rows.append(f"Current combat: atk {attack:.1f}/def {defense:.1f}")
        for area_id in state["unlocked_areas"]:
            area = areas[area_id]
            row = (
                f"{area_id}: {area['name']} need atk {area['requires_attack']}/def {area['requires_defense']} "
                f"progress {state['area_progress'].get(area_id, 0)}/{area['clears_required']} "
                f"clears {state['area_clears'].get(area_id, 0)}"
            )
            mechanic_text = boss_mechanics_text(area)
            if mechanic_text:
                row += f" | {mechanic_text}"
            rows.append(row)
        return "\n".join(rows)
    if primary == "goals":
        rows = []
        completed = set(state["completed_storylines"])
        if debug:
            for storyline in data["storylines"]:
                if storyline["id"] not in completed:
                    conditions = json.dumps(storyline.get("conditions", {}), sort_keys=True)
                    rows.append(
                        f"{storyline['id']}: {storyline['name']} - "
                        f"{storyline['description']} | conditions {conditions}"
                    )
            return "\n".join(rows) if rows else "All storylines complete."
        visible = visible_storyline_summaries(state, data)
        visible_ids = {goal["id"] for goal in visible}
        hidden_count = sum(
            1
            for storyline in data["storylines"]
            if storyline["id"] not in completed and storyline["id"] not in visible_ids
        )
        for goal in visible:
            rows.append(
                f"{goal['id']}: {goal['name']} - {goal['description']} "
                f"[{goal_progress_text(goal['progress'])}]"
            )
        if (
            state.get("retirement_unlocked")
            and state.get("retirements", 0) == 0
            and "astral_capstone" in completed
            and "echoed_foundation" not in completed
        ):
            rows.append("The lab feels ready for retirement; echoes may answer in the next run.")
        if hidden_count:
            rows.append(f"{hidden_count} distant storyline(s) remain hidden.")
        return "\n".join(rows) if rows else "All storylines complete."
    if primary == "automation":
        assignments = state.get("assignments", {})
        if not assignments:
            return "No active automation. Use assign <spell> <count> to start, unassign <spell> to stop."
        rows = [
            f"{spell_id}: {count} wizard(s)"
            for spell_id, count in sorted(assignments.items())
        ]
        return "\n".join(rows)
    if primary == "buffs":
        buffs = state.get("buffs", {})
        if not buffs:
            return "No active buffs."
        rows = []
        for buff_id, buff in sorted(buffs.items()):
            parts = [effect_part_text(key, value) for key, value in buff.items() if key != "duration"]
            parts.append(f"duration {buff.get('duration', 0)}")
            rows.append(f"{buff_id}: " + ", ".join(parts))
        return "\n".join(rows)
    if primary == "crit":
        crit = crit_public_state(state, data)
        if crit["mode"] == "charge":
            return (
                "Crit mode: charge\n"
                f"Focus charge: {crit['charge']}/{crit['max_charge']}\n"
                f"At full charge, the next explore gains +{crit['charge_bonus'] * 100:.0f}% attack and spends all charge.\n"
                f"Successful non-critical explores add {crit['charge_gain']} charge. Charge persists across battles and resets on retirement."
            )
        last = crit.get("last") or {}
        last_text = "none"
        if last:
            last_text = crit_event_text(last)
        return (
            "Crit mode: random\n"
            f"Chance: {crit['random_chance'] * 100:.0f}% per explore\n"
            f"Bonus: +{crit['random_bonus'] * 100:.0f}% attack on crit\n"
            f"Roll index: {crit['roll_index']}\n"
            f"Seed hash: {crit['seed_hash']}\n"
            f"Last roll: {last_text}"
        )
    if primary == "actions":
        return "\n".join(
            f"{name}: {ticks} tick{'s' if ticks != 1 else ''}"
            for name, ticks in sorted(ACTION_TICKS.items())
        ) + "\nbatch cast and batch transmute cost 1 tick per batch.\nassign, unassign, save, and retire are instant."
    if primary in {"reference", "references", "ref", "refs"}:
        return reference_text(state, data)
    return "Usage: list <spells|recipes|areas|goals|goals debug|automation|buffs|crit|actions|reference>"


def help_text() -> str:
    return """Commands:
  status
  list spells | list recipes | list areas | list goals | list goals debug | list automation | list buffs | list crit | list actions | list reference
  study <element> [turns]
  cast <spell>
  batch cast <spell[@priority] ...>
  batch transmute <recipe[@priority] ...>
  assign <spell> <count>
  unassign [spell ...]
  hire [count]
  explore <area> [times]
  transmute <recipe> [count]
  enhance <recipe> [levels]
  tick [turns]
  retire
  save
  quit
Use list reference for planning references, known buff durations, batch semantics, and route discipline.
"""


def execute(command: str, state: dict[str, Any], data: dict[str, Any]) -> tuple[bool, str]:
    stripped = command.strip()
    if not stripped or stripped.startswith("#"):
        return True, ""
    parts = stripped.split()
    verb, args = parts[0].lower(), parts[1:]
    if verb == "help":
        return True, help_text()
    if verb == "status":
        return True, cmd_status(state, data)
    if verb == "study":
        return True, cmd_study(args, state, data)
    if verb == "cast":
        return True, cmd_cast(args, state, data)
    if verb == "batch":
        return True, cmd_batch(args, state, data)
    if verb == "tick":
        return True, cmd_tick(args, state, data)
    if verb == "assign":
        return True, cmd_assign(args, state, data)
    if verb == "unassign":
        return True, cmd_unassign(args, state)
    if verb == "hire":
        return True, cmd_hire(args, state, data)
    if verb == "explore":
        return True, cmd_explore(args, state, data)
    if verb == "transmute":
        return True, cmd_transmute(args, state, data)
    if verb == "enhance":
        return True, cmd_enhance(args, state, data)
    if verb == "retire":
        return True, cmd_retire(state, data)
    if verb == "list":
        return True, cmd_list(" ".join(args) if args else "", state, data)
    if verb == "save":
        return True, "Saved."
    if verb in {"quit", "exit"}:
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
    parser = argparse.ArgumentParser(description="Run the Arcane Lab text RPG environment.")
    parser.add_argument("--state", type=Path, default=DEFAULT_SAVE, help="Path to a JSON save file.")
    parser.add_argument("--script", type=Path, help="Run commands from a script file.")
    parser.add_argument("--new", action="store_true", help="Start from a fresh state.")
    parser.add_argument(
        "--crit-mode",
        choices=sorted(CRIT_MODE_ALIASES),
        help="Crit rule mode for a new or loaded state: charge/deterministic or random/stochastic.",
    )
    parser.add_argument("--crit-seed", help="Seed for random crit mode. Ignored by charge except for state metadata.")
    parser.add_argument("--crit-charge-bonus", type=float, help="Base charge-mode attack bonus at full focus.")
    parser.add_argument("--crit-random-chance", type=float, help="Base random-mode crit chance before buffs/equipment.")
    parser.add_argument("--crit-random-bonus", type=float, help="Base random-mode attack bonus on crit.")
    parser.add_argument("--no-save", action="store_true", help="Do not write state after running.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    data = load_data()
    state_path = args.state if args.state.is_absolute() else PLAYGROUND_ROOT / args.state
    state = load_state(state_path, data, args.new)
    if (
        args.crit_mode
        or args.crit_seed
        or args.crit_charge_bonus is not None
        or args.crit_random_chance is not None
        or args.crit_random_bonus is not None
    ):
        configure_crit_state(
            state,
            mode=args.crit_mode,
            seed=args.crit_seed,
            charge_bonus=args.crit_charge_bonus,
            random_chance=args.crit_random_chance,
            random_bonus=args.crit_random_bonus,
        )
    check_storylines(state, data)
    if args.script:
        if args.script.is_absolute():
            script_path = args.script
        else:
            script_path = ROOT / args.script
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
