from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from sdk import LedgerTowerServerSDK  # noqa: E402


DEFAULT_ROUTE = Path("logs") / "route.txt"
DEFAULT_SUMMARY = Path("logs") / "official_submission.json"
DEFAULT_TRACKING = Path("logs") / "official_tracking.json"
PROMPT_VARS = Path(".runner") / "prompt.vars.json"
ALLOWED_VERBS = {"move", "go", "north", "east", "south", "west", "n", "e", "s", "w", "buy"}
DEFAULT_MAX_CONSECUTIVE_INVALID = 5


def workspace_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else WORKSPACE / candidate


def load_prompt_vars(path: Path = PROMPT_VARS) -> dict[str, Any]:
    resolved = workspace_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def strip_list_prefix(line: str) -> str:
    line = re.sub(r"^\s*[-*]\s+", "", line)
    line = re.sub(r"^\s*\d+[.)]\s+", "", line)
    return line.strip()


def parse_route(path: Path) -> list[str]:
    raw = workspace_path(path).read_text(encoding="utf-8-sig")
    stripped = raw.strip()
    if not stripped:
        raise ValueError(f"route file is empty: {path}")

    if stripped.startswith("[") or stripped.startswith("{"):
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            payload = payload.get("commands")
        if not isinstance(payload, list):
            raise ValueError("JSON route must be a list or an object with a commands list")
        commands = [str(command).strip() for command in payload]
    else:
        commands = []
        for raw_line in raw.splitlines():
            line = strip_list_prefix(raw_line)
            if line.startswith("```"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if not line or line.startswith("#"):
                continue
            commands.append(line)

    commands = [command for command in commands if command]
    if not commands:
        raise ValueError(f"route file has no commands: {path}")
    return commands


def validate_route(commands: list[str], *, max_commands: int, allow_inspection: bool) -> None:
    if len(commands) > max_commands:
        raise ValueError(f"route has {len(commands)} commands, above max {max_commands}")
    if allow_inspection:
        return
    bad: list[tuple[int, str]] = []
    for index, command in enumerate(commands, start=1):
        verb = command.split(maxsplit=1)[0].lower()
        if verb not in ALLOWED_VERBS:
            bad.append((index, command))
    if bad:
        sample = "; ".join(f"{index}: {command}" for index, command in bad[:5])
        raise ValueError(
            "official route may contain only movement and buy commands; "
            f"inspection or unsupported commands found: {sample}"
        )


def final_state(observation: dict[str, Any]) -> dict[str, Any]:
    player = observation.get("state") or {}
    score = observation.get("score") or {}
    metrics = score.get("metrics") or {}
    return {
        "moves": observation.get("moves"),
        "floor": observation.get("floor"),
        "hp": player.get("hp"),
        "atk": player.get("atk"),
        "def": player.get("def"),
        "gold": player.get("gold"),
        "keys": player.get("keys"),
        "inventory": player.get("inventory"),
        "victory": metrics.get("victory"),
        "route_score": score.get("route_score", metrics.get("route_score")),
        "reward": score.get("reward"),
        "failed_commands": metrics.get("failed_commands"),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(path: Path, payload: dict[str, Any], prompt_vars: dict[str, Any]) -> None:
    verification = payload.get("verification") or {}
    final = payload.get("final") or {}
    goal_completion = verification.get("goalCompletion") or {}
    lines = [
        "# Ledger Tower Official Route Submission",
        "",
        f"- model: `{prompt_vars.get('MODEL', '')}`",
        f"- runner: `{prompt_vars.get('RUNNER_CLIENT', '')}`",
        f"- track: `{prompt_vars.get('TRACK', '')}`",
        f"- official game id: `{payload.get('game_id')}`",
        f"- accepted: `{verification.get('accepted')}`",
        f"- outcome: `{verification.get('outcome')}`",
        f"- goalAchieved: `{verification.get('goalAchieved')}`",
        f"- failed goal keys: `{goal_completion.get('failed')}`",
        f"- reward: `{verification.get('reward')}`",
        f"- route_score: `{final.get('route_score')}`",
        f"- moves: `{final.get('moves')}`",
        f"- floor: `{final.get('floor')}`",
        f"- hp: `{final.get('hp')}`",
        f"- attack: `{final.get('atk')}`",
        f"- defense: `{final.get('def')}`",
        f"- gold: `{final.get('gold')}`",
        f"- keys: `{final.get('keys')}`",
        f"- inventory: `{final.get('inventory')}`",
        f"- victory: `{final.get('victory')}`",
        f"- softStopTick: `{verification.get('softStopTick')}`",
        f"- softStopScoring: `{verification.get('softStopScoring')}`",
        f"- softStopExceeded: `{verification.get('softStopExceeded')}`",
        f"- softStopScore: `{verification.get('softStopScore')}`",
        f"- stopped early: `{payload.get('stopped_early')}`",
        f"- stop reason: `{payload.get('stop_reason')}`",
        f"- failed/non-moving commands: `{payload.get('failed_command_count')}`",
        f"- max consecutive invalid before stop: `{payload.get('max_consecutive_invalid')}`",
        "",
        "## Commands",
        "",
    ]
    lines.extend(f"{index}. `{command}`" for index, command in enumerate(payload.get("commands", []), start=1))
    invalid_commands = payload.get("invalid_commands") or []
    if invalid_commands:
        lines.extend([
            "",
            "## Invalid Commands",
            "",
        ])
        for record in invalid_commands:
            output = str(record.get("output") or "").replace("\n", " / ")
            lines.append(
                f"- `{record.get('index')}` `{record.get('command')}` "
                f"at moves `{record.get('before_moves')}`: {output}"
            )
    lines.extend([
        "",
        "## Notes",
        "",
        "Submitted through the runner-provided route helper. The helper created one official game, executed the route file in order, called `verify()`, and wrote this report. Non-moving commands are recorded and penalized by route-quality summaries; the helper stops early only after too many consecutive non-moving commands.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit a Ledger Tower route as one official attempt.")
    parser.add_argument("--route", default=str(DEFAULT_ROUTE), help="Route file. Text lines or JSON commands list.")
    parser.add_argument("--summary-json", default=str(DEFAULT_SUMMARY), help="Output JSON summary path.")
    parser.add_argument("--tracking-json", default=str(DEFAULT_TRACKING), help="Output server trajectory export path.")
    parser.add_argument("--report", default="", help="Markdown report path. Defaults to prompt vars REPORT_PATH.")
    parser.add_argument("--label", default="", help="Official game label. Defaults to prompt vars LABEL.")
    parser.add_argument("--max-commands", type=int, default=500)
    parser.add_argument(
        "--max-consecutive-invalid",
        type=int,
        default=DEFAULT_MAX_CONSECUTIVE_INVALID,
        help=(
            "Stop replay after this many consecutive commands do not spend a move. "
            f"Default: {DEFAULT_MAX_CONSECUTIVE_INVALID}."
        ),
    )
    parser.add_argument(
        "--strict-invalid-stop",
        action="store_true",
        help="Legacy strict mode: stop after the first command that does not spend a move.",
    )
    parser.add_argument("--allow-inspection", action="store_true", help="Allow free inspection commands in the route.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate only; do not create an official game.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    prompt_vars = load_prompt_vars()
    route_path = Path(args.route)
    summary_path = workspace_path(args.summary_json)
    tracking_path = workspace_path(args.tracking_json)
    report_path = workspace_path(args.report or prompt_vars.get("REPORT_PATH") or "logs/official_report.md")
    label = args.label or str(prompt_vars.get("LABEL") or "ledger-tower-route-submit")
    invalid_stop_limit = 1 if args.strict_invalid_stop else max(1, int(args.max_consecutive_invalid))

    try:
        commands = parse_route(route_path)
        validate_route(commands, max_commands=args.max_commands, allow_inspection=bool(args.allow_inspection))
    except Exception as exc:
        payload = {
            "ok": False,
            "phase": "validation",
            "error": str(exc),
            "route": str(route_path),
        }
        write_json(summary_path, payload)
        print(f"route validation failed: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        payload = {
            "ok": True,
            "phase": "dry-run",
            "route": str(route_path),
            "command_count": len(commands),
            "commands": commands,
        }
        write_json(summary_path, payload)
        print(f"validated {len(commands)} route commands; no official game created")
        return 0

    stopped_early = False
    stop_reason = ""
    step_records: list[dict[str, Any]] = []
    invalid_commands: list[dict[str, Any]] = []
    verification: dict[str, Any] | None = None
    observation: dict[str, Any] | None = None
    game_id: str | None = None

    try:
        tower = LedgerTowerServerSDK(new=True, label=label)
        game_id = tower.game_id
        observation = tower.observe(include_text=False)
        consecutive_invalid = 0
        for index, command in enumerate(commands, start=1):
            before_moves = int((observation or {}).get("moves") or 0)
            result = tower.step(command)
            observation = result.observation
            after_moves = int((observation or {}).get("moves") or 0)
            moved = after_moves > before_moves
            if not moved:
                consecutive_invalid += 1
                invalid_commands.append({
                    "index": index,
                    "command": command,
                    "before_moves": before_moves,
                    "after_moves": after_moves,
                    "output": result.output,
                })
            else:
                consecutive_invalid = 0
            step_records.append({
                "index": index,
                "command": command,
                "before_moves": before_moves,
                "after_moves": after_moves,
                "moved": moved,
                "done": result.done,
                "output": result.output,
            })
            if consecutive_invalid >= invalid_stop_limit:
                stopped_early = True
                stop_reason = f"{consecutive_invalid} consecutive command(s) did not spend a move"
                break
            if result.done:
                break
        verification = tower.verify()
        try:
            tower.export_tracking(tracking_path)
        except Exception as exc:  # Export is useful but should not hide verification.
            step_records.append({"warning": f"tracking export failed: {exc}"})
        observation = tower.observe(include_text=False)
    except Exception as exc:
        payload = {
            "ok": False,
            "phase": "submission",
            "error": str(exc),
            "game_id": game_id,
            "route": str(route_path),
            "command_count": len(commands),
            "commands": commands,
            "steps": step_records,
            "invalid_commands": invalid_commands,
            "failed_command_count": len(invalid_commands),
            "max_consecutive_invalid": invalid_stop_limit,
            "strict_invalid_stop": bool(args.strict_invalid_stop),
        }
        write_json(summary_path, payload)
        print(f"official submission failed: {exc}", file=sys.stderr)
        return 3

    payload = {
        "ok": True,
        "phase": "submitted",
        "game_id": game_id,
        "route": str(route_path),
        "command_count": len(commands),
        "commands": commands,
        "steps": step_records,
        "invalid_commands": invalid_commands,
        "failed_command_count": len(invalid_commands),
        "max_consecutive_invalid": invalid_stop_limit,
        "strict_invalid_stop": bool(args.strict_invalid_stop),
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
        "verification": verification,
        "final": final_state(observation or {}),
        "report": str(report_path),
        "tracking": str(tracking_path),
    }
    write_json(summary_path, payload)
    write_report(report_path, payload, prompt_vars)
    print(json.dumps({
        "game_id": game_id,
        "reward": verification.get("reward") if verification else None,
        "accepted": verification.get("accepted") if verification else None,
        "outcome": verification.get("outcome") if verification else None,
        "report": str(report_path),
        "summary": str(summary_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
