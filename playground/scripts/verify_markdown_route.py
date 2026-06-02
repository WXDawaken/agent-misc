from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def extract_fenced_commands(route_path: Path) -> list[str]:
    commands: list[str] = []
    in_fence = False
    collect = False
    for raw in route_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("```"):
            if not in_fence:
                lang = line[3:].strip().lower()
                in_fence = True
                collect = lang in {"", "text", "txt", "commands"}
            else:
                in_fence = False
                collect = False
            continue
        if not in_fence or not collect:
            continue
        if not line or line.startswith("#"):
            continue
        commands.append(line)
    return commands


def load_track_config(config_path: Path, track: str) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    track_config = config["tracks"][track]
    goal = dict(track_config["goal"])
    goal["tick_budget"] = int(track_config["tick_budget"])
    soft_stop_tick = None
    if track_config.get("soft_stop") is not False:
        if "soft_stop_tick" in track_config:
            configured_tick = track_config.get("soft_stop_tick")
            soft_stop_tick = None if configured_tick is None else int(configured_tick)
        else:
            configured_gap = track_config.get("soft_stop_gap", 0)
            if configured_gap is not None:
                soft_stop_tick = int(track_config["tick_budget"]) - int(configured_gap)
    return {
        "goal": goal,
        "tick_budget": int(track_config["tick_budget"]),
        "soft_stop_tick": soft_stop_tick,
    }


def summarize_score(score: dict[str, Any]) -> dict[str, Any]:
    metrics = score.get("metrics", {})
    completion = score.get("goal_completion", {})
    return {
        "reward": score.get("reward"),
        "goal_achieved": score.get("goal_achieved"),
        "goal_completion": completion,
        "tick": metrics.get("tick"),
        "lifetime_tick": metrics.get("lifetime_tick"),
        "run": metrics.get("run"),
        "retirements": metrics.get("retirements"),
        "insight": metrics.get("insight"),
    }


def summarize_verify(verify: dict[str, Any]) -> dict[str, Any]:
    return {
        "outcome": verify.get("outcome"),
        "accepted": verify.get("accepted"),
        "goalAchieved": verify.get("goalAchieved"),
        "reward": verify.get("reward"),
        "tickBudgetUsed": verify.get("tickBudgetUsed"),
        "tickBudget": verify.get("tickBudget"),
        "softStopExceeded": verify.get("softStopExceeded"),
        "softStopUsed": verify.get("softStopUsed"),
        "softStopScoring": verify.get("softStopScoring"),
        "softStopScore": verify.get("softStopScore"),
        "trajectory_hash": verify.get("trajectory_hash"),
    }


def flagged_outputs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers = (
        "fail",
        "failed",
        "cannot",
        "unknown",
        "not available",
        "not enough",
        "locked",
        "stopped",
    )
    flagged: list[dict[str, Any]] = []
    for entry in entries:
        output = str(entry.get("output", ""))
        lowered = output.lower()
        if any(marker in lowered for marker in markers):
            flagged.append(
                {
                    "index": entry["index"],
                    "command": entry["command"],
                    "tick": entry.get("tick"),
                    "lifetime_tick": entry.get("lifetime_tick"),
                    "first_output_line": output.splitlines()[0] if output else "",
                }
            )
    return flagged


def console_view(result: dict[str, Any]) -> dict[str, Any]:
    view = {
        key: value
        for key, value in result.items()
        if key not in {"entries", "final_observation", "score"}
    }
    if "verify" in view:
        view["verify"] = summarize_verify(view["verify"])
    if "server_result" in view:
        view["server_result"] = console_view(view["server_result"])
    return view


def run_local(
    *,
    workspace: Path,
    commands: list[str],
    goal: dict[str, Any],
    crit_mode: str,
    crit_seed: str,
) -> dict[str, Any]:
    sys.path.insert(0, str(workspace))
    from sdk import ArcaneLabSDK  # noqa: E402

    lab = ArcaneLabSDK(new=True, crit_mode=crit_mode, crit_seed=crit_seed)
    entries: list[dict[str, Any]] = []
    stopped_early = False
    for index, command in enumerate(commands, start=1):
        result = lab.step(command)
        observation = result.observation or lab.observe(include_text=False)
        entries.append(
            {
                "index": index,
                "command": command,
                "tick": observation.get("tick"),
                "lifetime_tick": observation.get("lifetime_tick"),
                "run": observation.get("run"),
                "output": result.output,
                "done": result.done,
            }
        )
        if result.done:
            stopped_early = index < len(commands)
            break
    score = lab.score(goal)
    observation = lab.observe(include_text=False)
    return {
        "mode": "local",
        "workspace": str(workspace),
        "command_count": len(commands),
        "executed_command_count": len(entries),
        "stopped_early": stopped_early,
        "summary": summarize_score(score),
        "score": score,
        "final_observation": observation,
        "flagged_outputs": flagged_outputs(entries),
        "entries": entries,
    }


def run_server(
    *,
    workspace: Path,
    commands: list[str],
    goal: dict[str, Any],
    base_url: str,
    auth_token: str,
    soft_stop_tick: int | None,
    label: str,
) -> dict[str, Any]:
    sys.path.insert(0, str(workspace))
    from sdk import ArcaneLabServerSDK  # noqa: E402

    lab = ArcaneLabServerSDK(base_url=base_url, auth_token=auth_token, new=True, label=label)
    entries: list[dict[str, Any]] = []
    stopped_early = False
    for index, command in enumerate(commands, start=1):
        result = lab.step(command)
        observation = result.observation or lab.observe(include_text=False)
        entries.append(
            {
                "index": index,
                "command": command,
                "tick": observation.get("tick"),
                "lifetime_tick": observation.get("lifetime_tick"),
                "run": observation.get("run"),
                "output": result.output,
                "done": result.done,
            }
        )
        if result.done:
            stopped_early = index < len(commands)
            break
    score = lab.score(goal)
    verify = lab.verify(goal=goal, tick_budget=goal["tick_budget"], soft_stop_tick=soft_stop_tick)
    observation = lab.observe(include_text=False)
    return {
        "mode": "server",
        "server": base_url,
        "game_id": lab.game_id,
        "command_count": len(commands),
        "executed_command_count": len(entries),
        "stopped_early": stopped_early,
        "summary": summarize_score(score),
        "score": score,
        "verify": verify,
        "final_observation": observation,
        "flagged_outputs": flagged_outputs(entries),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a markdown final_route.md through Arcane Lab.")
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("envs/arcane_lab/docs/tracks/config.json"))
    parser.add_argument("--track", default="budgeted-prestige")
    parser.add_argument("--crit-mode", default="random")
    parser.add_argument("--crit-seed", default="practice-seed")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--server-url")
    parser.add_argument("--auth-token")
    parser.add_argument("--label", default="verify-markdown-route")
    args = parser.parse_args()

    commands = extract_fenced_commands(args.route)
    track = load_track_config(args.config, args.track)
    result = run_local(
        workspace=args.workspace.resolve(),
        commands=commands,
        goal=track["goal"],
        crit_mode=args.crit_mode,
        crit_seed=args.crit_seed,
    )
    if args.server_url and args.auth_token:
        result["server_result"] = run_server(
            workspace=args.workspace.resolve(),
            commands=commands,
            goal=track["goal"],
            base_url=args.server_url,
            auth_token=args.auth_token,
            soft_stop_tick=track["soft_stop_tick"],
            label=args.label,
        )
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
        print(json.dumps(console_view(result), indent=2, sort_keys=True))
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
