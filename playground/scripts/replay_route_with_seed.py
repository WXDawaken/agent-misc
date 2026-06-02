from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE_MODULE = (
    ROOT
    / "agent_workspaces"
    / "opencode_runs"
    / "opencode-go-openai_gpt-5.5-budgeted-prestige_20260509_165603"
    / "logs"
    / "official_run.py"
)
DEFAULT_OUT_DIR = ROOT / "logs" / "seed_replays"


def load_route_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("frozen_route_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load route module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "ROUTE") or not hasattr(module, "GOAL"):
        raise RuntimeError(f"route module must define ROUTE and GOAL: {path}")
    return module


def mint_token(
    *,
    task_id: str,
    goal: dict[str, Any],
    tick_budget: int,
    soft_stop_tick: int,
    crit_mode: str,
    crit_seed: str,
    crit_random_chance: float | None,
    crit_random_bonus: float | None,
    ttl_seconds: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "server.py",
        "mint-token",
        "--task-id",
        task_id,
        "--max-new-games",
        "1",
        "--ttl-seconds",
        str(ttl_seconds),
        "--goal-json",
        json.dumps(goal, separators=(",", ":")),
        "--tick-budget",
        str(tick_budget),
        "--soft-stop-tick",
        str(soft_stop_tick),
        "--crit-mode",
        crit_mode,
        "--crit-seed",
        crit_seed,
    ]
    if crit_random_chance is not None:
        command.extend(["--crit-random-chance", str(crit_random_chance)])
    if crit_random_bonus is not None:
        command.extend(["--crit-random-bonus", str(crit_random_bonus)])
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"mint-token failed: {completed.stderr or completed.stdout}")
    return json.loads(completed.stdout)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "seed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a frozen Arcane Lab route with a specified server crit seed.")
    parser.add_argument("--route-module", type=Path, default=DEFAULT_ROUTE_MODULE)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--label", default="operator-seed-replay")
    parser.add_argument("--tag", default="route", help="Short tag used in the replay task id and output filename.")
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    parser.add_argument("--tick-budget", type=int, default=260)
    parser.add_argument("--soft-stop-tick", type=int, default=240)
    parser.add_argument("--crit-mode", default="random")
    parser.add_argument("--crit-random-chance", type=float, default=0.18)
    parser.add_argument("--crit-random-bonus", type=float, default=0.2)
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    route_module = load_route_module(args.route_module)
    route = list(route_module.ROUTE)
    goal = dict(route_module.GOAL)
    task_id = f"seed-replay-{safe_name(args.tag)}-{time.strftime('%Y%m%d_%H%M%S')}-{safe_name(args.seed)}"

    token_info = mint_token(
        task_id=task_id,
        goal=goal,
        tick_budget=args.tick_budget,
        soft_stop_tick=args.soft_stop_tick,
        crit_mode=args.crit_mode,
        crit_seed=args.seed,
        crit_random_chance=args.crit_random_chance,
        crit_random_bonus=args.crit_random_bonus,
        ttl_seconds=args.ttl_seconds,
    )

    sdk_class = route_module.ArcaneLabServerSDK
    lab = sdk_class(
        base_url=args.server_url,
        new=True,
        label=args.label,
        auth_token=token_info["token"],
    )

    commands: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    crit_events: list[dict[str, Any]] = []
    for index, command in enumerate(route, start=1):
        result = lab.step(command)
        obs = result.observation
        commands.append(
            {
                "index": index,
                "command": command,
                "lifetime_tick": obs.get("lifetime_tick"),
                "tick": obs.get("tick"),
                "run": obs.get("run"),
                "output": result.output,
            }
        )
        lowered = result.output.lower()
        if "fail" in lowered or "cannot" in lowered or "unknown" in lowered:
            failures.append({"index": index, "command": command, "output": result.output})
        last_crit = (obs.get("crit") or {}).get("last")
        if command.startswith("explore") and last_crit:
            crit_events.append(
                {
                    "index": index,
                    "command": command,
                    "roll_index": last_crit.get("roll_index"),
                    "roll": last_crit.get("roll"),
                    "chance": last_crit.get("chance"),
                    "triggered": last_crit.get("triggered"),
                    "attack_before": last_crit.get("attack_before"),
                    "attack_after": last_crit.get("attack_after"),
                    "success": last_crit.get("success"),
                }
            )

    final_obs = lab.observe(include_text=False)
    verification = lab.verify(goal)
    result = {
        "task_id": task_id,
        "seed": args.seed,
        "token_hash": token_info.get("token_hash"),
        "crit_seed_hash": token_info.get("crit_seed_hash"),
        "game_id": lab.game_id,
        "route_module": str(args.route_module),
        "command_count": len(commands),
        "failure_count": len(failures),
        "crit_trigger_count": sum(1 for event in crit_events if event.get("triggered")),
        "crit_events": crit_events,
        "failures": failures,
        "final": final_obs,
        "verification": verification,
        "commands": commands,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"{task_id}.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "out_path": str(out_path),
                "seed": args.seed,
                "crit_seed_hash": token_info.get("crit_seed_hash"),
                "game_id": lab.game_id,
                "accepted": verification.get("accepted"),
                "outcome": verification.get("outcome"),
                "goal_achieved": verification.get("goalAchieved"),
                "reward": verification.get("reward"),
                "lifetime_tick": final_obs.get("lifetime_tick"),
                "run": final_obs.get("run"),
                "tick": final_obs.get("tick"),
                "retirements": final_obs.get("retirements"),
                "insight": final_obs.get("insight"),
                "failure_count": len(failures),
                "crit_trigger_count": result["crit_trigger_count"],
                "trajectory_hash": verification.get("trajectory_hash"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
