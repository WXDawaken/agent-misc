from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE = Path.cwd().resolve()
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from sdk import ArcaneLabSDK, ArcaneLabServerSDK


HELPER_DIRECTIVES = """
Route scripts live under logs\\ and may mix game commands with zero-tick helper
directives:
  checkpoint after_gear
  expect area gear_sanctum clears >= 1
  expect resources.paper >= 16
  expect buff route_sketch active
  expect recipe astral_array known
  expect recipe echo_anchor owned
  expect goal achieved
""".strip()


GOAL = {
    "storyline": "echo_vault_attuned",
    "recipe": "echo_anchor",
    "area": "echo_vault",
    "area_clears": 1,
    "retirements": 1,
    "insight": 12,
    "run": 2,
}


def workspace_path(raw: str | None, default: str) -> Path:
    path = Path(raw or default)
    if not path.is_absolute():
        path = WORKSPACE / path
    resolved = path.resolve()
    logs_root = (WORKSPACE / "logs").resolve()
    if not (resolved == logs_root or logs_root in resolved.parents):
        raise SystemExit("helper outputs must stay under logs\\")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def route_script_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = WORKSPACE / path
    resolved = path.resolve()
    logs_root = (WORKSPACE / "logs").resolve()
    if not (resolved == logs_root or logs_root in resolved.parents):
        raise SystemExit("helper route scripts must stay under logs\\")
    return resolved


def parse_route_item(line: str, source: str) -> dict[str, Any]:
    lowered = line.lower()
    if lowered.startswith("expect ") or lowered.startswith("assert "):
        return {"kind": "expect", "text": line.split(maxsplit=1)[1].strip(), "source": source}
    if lowered.startswith("checkpoint "):
        return {"kind": "checkpoint", "text": line.split(maxsplit=1)[1].strip(), "source": source}
    return {"kind": "command", "text": line, "source": source}


def load_route_items(
    path: Path | None,
    inline_commands: list[str],
    inline_expects: list[str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if path:
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if line and not line.startswith("#"):
                items.append(parse_route_item(line, f"{path}:{line_number}"))
    items.extend(
        {"kind": "command", "text": command.strip(), "source": "--cmd"}
        for command in inline_commands
        if command.strip()
    )
    items.extend(
        {"kind": "expect", "text": expr.strip(), "source": "--expect"}
        for expr in inline_expects
        if expr.strip()
    )
    return items


def compact(obs: dict[str, Any]) -> dict[str, Any]:
    resources = obs.get("resources", {})
    combat = obs.get("combat", {})
    mana = obs.get("mana", {})
    hp = obs.get("hp", {})
    return {
        "run": obs.get("run"),
        "tick": obs.get("tick"),
        "lifetime_tick": obs.get("lifetime_tick"),
        "mana": {"current": mana.get("current"), "max": mana.get("max"), "rate": mana.get("rate")},
        "hp": {"current": hp.get("current"), "max": hp.get("max")},
        "combat": {"attack": combat.get("attack"), "defense": combat.get("defense")},
        "resources": resources,
        "insight": obs.get("insight"),
        "retirements": obs.get("retirements"),
        "equipment": obs.get("equipment"),
        "equipment_levels": obs.get("equipment_levels"),
        "equipment_spares": obs.get("equipment_spares"),
        "buffs": obs.get("buffs"),
        "assignments": obs.get("assignments"),
        "crit": obs.get("crit"),
        "known_spells": obs.get("known_spells"),
        "known_recipes": obs.get("known_recipes"),
        "completed_storylines": obs.get("completed_storylines"),
        "next_goals": obs.get("next_goals"),
        "areas": {
            key: {
                "progress": value.get("progress"),
                "clears": value.get("clears"),
                "requires_attack": value.get("requires_attack"),
                "requires_defense": value.get("requires_defense"),
                "boss": value.get("boss"),
            }
            for key, value in (obs.get("areas") or {}).items()
        },
        "score": obs.get("score"),
    }


def command_failed(output: str) -> bool:
    lowered = output.lower()
    return any(
        marker in lowered
        for marker in ("failed", "not enough", "cannot", "unknown", "stopped:")
    )


def goal_completion(score: dict[str, Any]) -> dict[str, Any]:
    completion = score.get("goal_completion")
    if not isinstance(completion, dict):
        return {"achieved": None, "achievedCount": 0, "total": 0, "failed": []}
    failed = list(completion.get("failed", []))
    total = int(completion.get("total", 0) or 0)
    achieved_count = int(completion.get("achieved_count", total - len(failed)) or 0)
    return {
        "achieved": completion.get("achieved"),
        "achievedCount": achieved_count,
        "total": total,
        "failed": failed,
    }


def verification_outcome(accepted: bool, achieved: bool | None) -> str:
    if not accepted:
        return "rejected"
    if achieved is False:
        return "partial"
    if achieved is True:
        return "success"
    return "accepted"


def local_verify(lab: Any, goal: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    score = lab.score(goal)
    completion = goal_completion(score)
    achieved = completion["achieved"]
    return {
        "accepted": True,
        "outcome": verification_outcome(True, achieved),
        "goalAchieved": achieved,
        "goalCompletion": completion,
        "official": False,
        "reward": int(score.get("reward", 0)),
        "score": score,
        "goal": goal,
        "tickBudgetUsed": obs.get("lifetime_tick"),
        "tickBudgetType": "lifetime",
        "final": compact(obs),
    }


def resolve_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
    return current


def parse_expected(raw: str) -> Any:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if lowered in ("none", "null"):
        return None
    try:
        if any(marker in value for marker in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def as_number(value: Any) -> float | None:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def compare_values(actual: Any, op: str, expected: Any) -> bool:
    if op in (">=", "<=", ">", "<"):
        actual_number = as_number(actual)
        expected_number = as_number(expected)
        if actual_number is None or expected_number is None:
            return False
        if op == ">=":
            return actual_number >= expected_number
        if op == "<=":
            return actual_number <= expected_number
        if op == ">":
            return actual_number > expected_number
        return actual_number < expected_number
    if op in ("==", "="):
        if isinstance(expected, (int, float)) and actual is None:
            actual = 0
        return actual == expected
    if op == "!=":
        if isinstance(expected, (int, float)) and actual is None:
            actual = 0
        return actual != expected
    if op == "contains":
        if isinstance(actual, dict):
            return str(expected) in actual
        if isinstance(actual, list):
            return expected in actual or str(expected) in [str(item) for item in actual]
        return str(expected) in str(actual or "")
    if op in ("not_contains", "not-contains"):
        return not compare_values(actual, "contains", expected)
    if op == "exists":
        return actual is not None
    if op == "missing":
        return actual is None
    raise ValueError(f"unknown assertion operator: {op}")


def assert_path(payload: dict[str, Any], expr: str) -> dict[str, Any]:
    parts = expr.split()
    if len(parts) == 2 and parts[1] in ("exists", "missing"):
        path, op = parts
        expected = None
    elif len(parts) >= 3:
        path, op = parts[0], parts[1]
        expected = parse_expected(" ".join(parts[2:]))
    else:
        raise ValueError("expected '<path> <op> <value>'")
    actual = resolve_path(payload, path)
    passed = compare_values(actual, op, expected)
    return {"expr": expr, "passed": passed, "actual": actual, "op": op, "expected": expected}


def assert_friendly(lab: Any, obs: dict[str, Any], failures: list[dict[str, Any]], expr: str) -> dict[str, Any] | None:
    lowered = expr.lower()
    parts = expr.split()
    if lowered == "goal achieved":
        score = lab.score(GOAL)
        actual = score.get("goal_achieved")
        return {"expr": expr, "passed": actual is True, "actual": actual, "op": "is", "expected": True}
    if lowered == "no failures":
        actual = len(failures)
        return {"expr": expr, "passed": actual == 0, "actual": actual, "op": "==", "expected": 0}
    if len(parts) == 3 and parts[0] == "storyline" and parts[2] == "completed":
        actual = parts[1] in (obs.get("completed_storylines") or [])
        return {"expr": expr, "passed": actual, "actual": actual, "op": "is", "expected": True}
    if len(parts) == 3 and parts[0] == "recipe" and parts[2] == "known":
        actual = parts[1] in (obs.get("known_recipes") or [])
        return {"expr": expr, "passed": actual, "actual": actual, "op": "is", "expected": True}
    if len(parts) >= 3 and parts[0] in ("recipe", "equipment") and parts[2] == "owned":
        target = int(parts[3]) if len(parts) >= 4 else 1
        actual = int((obs.get("equipment") or {}).get(parts[1], 0) or 0)
        return {"expr": expr, "passed": actual >= target, "actual": actual, "op": ">=", "expected": target}
    if len(parts) == 3 and parts[0] == "area" and parts[2] == "unlocked":
        actual = parts[1] in (obs.get("areas") or {})
        return {"expr": expr, "passed": actual, "actual": actual, "op": "is", "expected": True}
    if len(parts) >= 5 and parts[0] == "area":
        path = f"areas.{parts[1]}.{parts[2]}"
        return assert_path(obs, f"{path} {parts[3]} {' '.join(parts[4:])}")
    if len(parts) == 3 and parts[0] == "buff" and parts[2] == "active":
        actual = resolve_path(obs, f"buffs.{parts[1]}.duration")
        return {"expr": expr, "passed": bool(actual and as_number(actual)), "actual": actual, "op": ">", "expected": 0}
    return None


def evaluate_expectation(
    lab: Any,
    obs: dict[str, Any],
    failures: list[dict[str, Any]],
    expr: str,
) -> dict[str, Any]:
    try:
        result = assert_friendly(lab, obs, failures, expr) or assert_path(obs, expr)
    except Exception as exc:  # noqa: BLE001 - assertion errors should be data, not crashes.
        return {"expr": expr, "passed": False, "error": str(exc)}
    return result


def make_lab(args: argparse.Namespace) -> Any:
    if args.server:
        return ArcaneLabServerSDK(new=args.new, label=args.label)
    state_path = workspace_path(args.state, "logs\\practice_state.json")
    if args.new or not state_path.exists():
        return ArcaneLabSDK(
            new=True,
            crit_mode=args.crit_mode,
            crit_seed=args.crit_seed,
            crit_charge_bonus=args.crit_charge_bonus,
            crit_random_chance=args.crit_random_chance,
            crit_random_bonus=args.crit_random_bonus,
        )
    return ArcaneLabSDK(state_path=str(state_path))


def emit_json(title: str, payload: Any) -> None:
    print(f"\n## {title}")
    print(json.dumps(payload, indent=2, sort_keys=True))


def run(args: argparse.Namespace) -> int:
    lab = make_lab(args)
    if args.list_kind:
        print(lab.list_available(args.list_kind))
    items = load_route_items(
        route_script_path(args.script),
        list(args.cmd or []),
        list(args.expect or []),
    )
    failures: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    stopped_on_assertion = False
    for item in items:
        if item["kind"] == "checkpoint":
            obs = lab.observe()
            emit_json(f"CHECKPOINT {item['text']}", compact(obs))
            continue
        if item["kind"] == "expect":
            obs = lab.observe()
            assertion = evaluate_expectation(lab, obs, failures, item["text"])
            assertion["source"] = item["source"]
            assertions.append(assertion)
            state = "PASS" if assertion.get("passed") else "FAIL"
            print(f"\n? {state} {item['text']}")
            if not assertion.get("passed"):
                print(json.dumps(assertion, indent=2, sort_keys=True))
                if args.stop_on_assert:
                    stopped_on_assertion = True
                    break
            continue
        command = item["text"]
        result = lab.step(command)
        print(f"\n> {command}")
        print(result.output)
        if args.state_each:
            emit_json("STATE", compact(result.observation))
        if command_failed(result.output):
            failures.append({"command": command, "output": result.output})
            if args.stop_on_failure:
                break

    obs = lab.observe()
    emit_json("FINAL", compact(obs))
    if failures:
        emit_json("FAILURES", failures)
    if assertions:
        emit_json("ASSERTIONS", {
            "passed": sum(1 for assertion in assertions if assertion.get("passed")),
            "failed": sum(1 for assertion in assertions if not assertion.get("passed")),
            "items": assertions,
        })
    if not args.server:
        save_path = workspace_path(args.save_state or args.state, "logs\\practice_state.json")
        lab.save(str(save_path))
        print(f"\nSaved direct practice state: {save_path}")
    verification = None
    if args.verify:
        verification = lab.verify(GOAL) if hasattr(lab, "verify") else local_verify(lab, GOAL, obs)
        emit_json("VERIFY", verification)
    if args.json_out:
        out_path = workspace_path(args.json_out, "logs\\helper_summary.json")
        out_path.write_text(
            json.dumps(
                {
                    "final": compact(obs),
                    "failures": failures,
                    "assertions": assertions,
                    "stopped_on_assertion": stopped_on_assertion,
                    "verification": verification,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote helper summary: {out_path}")
    assertion_failed = any(not assertion.get("passed") for assertion in assertions)
    return 1 if args.fail_exit and (failures or assertion_failed) else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Thin Arcane Lab route practice and assertion helper.",
        epilog=HELPER_DIRECTIVES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--server", action="store_true", help="Use ArcaneLabServerSDK instead of direct practice.")
    parser.add_argument("--new", action="store_true", help="Create a new direct or server game.")
    parser.add_argument("--label", default="provided-helper-prestige")
    parser.add_argument("--state", default="logs\\practice_state.json")
    parser.add_argument("--save-state", default="")
    parser.add_argument("--script", help="Command file, one command per line.")
    parser.add_argument("--cmd", action="append", default=[], help="Inline command. Repeatable.")
    parser.add_argument("--expect", action="append", default=[], help="Inline zero-tick assertion. Repeatable.")
    parser.add_argument("--list-kind", choices=["spells", "recipes", "areas", "goals", "automation", "buffs", "crit", "actions"])
    parser.add_argument("--state-each", action="store_true", help="Print compact state after each command.")
    parser.add_argument("--stop-on-failure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-assert", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fail-exit", action="store_true", help="Exit nonzero when a command or assertion failed.")
    parser.add_argument("--json-out", default="", help="Write helper summary JSON under logs\\.")
    parser.add_argument("--verify", action="store_true", help="Verify the track goal; server mode uses server verify.")
    parser.add_argument("--crit-mode", default="random")
    parser.add_argument("--crit-seed", default="practice-seed")
    parser.add_argument("--crit-charge-bonus", type=float)
    parser.add_argument("--crit-random-chance", type=float)
    parser.add_argument("--crit-random-bonus", type=float)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
