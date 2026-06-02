from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdk import ArcaneLabSDK  # noqa: E402
from server_core import normalize_soft_stop_scoring, soft_stop_score  # noqa: E402


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def parse_goal(args: argparse.Namespace) -> dict[str, Any]:
    goal: dict[str, Any] = {}
    if args.goal_storyline:
        goal["storyline"] = args.goal_storyline
    if args.goal_area:
        goal["area"] = args.goal_area
        goal["area_clears"] = args.goal_area_clears
    if args.goal_recipe:
        goal["recipe"] = args.goal_recipe
        goal["recipe_count"] = args.goal_recipe_count
    if args.goal_assignment:
        goal["assignment"] = args.goal_assignment
        goal["assignment_count"] = args.goal_assignment_count
    if args.goal_wizards is not None:
        goal["wizards"] = args.goal_wizards
    if args.goal_retirements is not None:
        goal["retirements"] = args.goal_retirements
    if args.goal_insight is not None:
        goal["insight"] = args.goal_insight
    if args.goal_run is not None:
        goal["run"] = args.goal_run
    if args.goal_unlocked_area:
        goal["unlocked_areas"] = args.goal_unlocked_area
    if args.tick_budget is not None:
        goal["tick_budget"] = args.tick_budget
    if args.lifetime_tick_budget is not None:
        goal["lifetime_tick_budget"] = args.lifetime_tick_budget
    if args.per_run_tick_budget is not None:
        goal["per_run_tick_budget"] = args.per_run_tick_budget
    if args.goal_area_progress:
        area, sep, target = args.goal_area_progress.partition(":")
        if not sep or not area or not target:
            raise SystemExit("--goal-area-progress must use AREA:STEPS, for example shaded_grove:2")
        try:
            target_steps = int(target)
        except ValueError as exc:
            raise SystemExit("--goal-area-progress STEPS must be an integer") from exc
        goal["area_progress"] = {"area": area, "target": target_steps}
    return goal


def reward_summary(reward_obj: dict[str, Any]) -> str:
    score = reward_obj["score"]
    goal_completion = reward_obj.get("goalCompletion", {})
    lines = [
        f"reward: {reward_obj['reward']}",
        f"accepted: {reward_obj.get('accepted')}",
        f"outcome: {reward_obj.get('outcome')}",
        f"goalAchieved: {reward_obj.get('goalAchieved')}",
        f"goalPassed: {goal_completion.get('achievedCount')} / {goal_completion.get('total')}",
        f"goalFailed: {', '.join(goal_completion.get('failed', [])) or '-'}",
        f"tickBudget: {reward_obj.get('tickBudget')}",
        f"tickBudgetType: {reward_obj.get('tickBudgetType')}",
        f"tickBudgetUsed: {reward_obj.get('tickBudgetUsed')}",
        f"tickBudgetExceeded: {reward_obj.get('tickBudgetExceeded')}",
        f"softStopTick: {reward_obj.get('softStopTick')}",
        f"softStopUsed: {reward_obj.get('softStopUsed')}",
        f"softStopExceeded: {reward_obj.get('softStopExceeded')}",
        f"softStopScoring: {reward_obj.get('softStopScoring')}",
        f"softStopScore: {reward_obj.get('softStopScore')}",
        f"perRunTickBudget: {reward_obj.get('perRunTickBudget')}",
        f"perRunTickBudgetUsed: {reward_obj.get('perRunTickBudgetUsed')}",
        f"perRunTickBudgetExceeded: {reward_obj.get('perRunTickBudgetExceeded')}",
    ]
    metrics = score.get("metrics", {})
    if metrics:
        lines.append(f"tick: {metrics.get('tick')}")
        lines.append(f"lifetime_tick: {metrics.get('lifetime_tick')}")
        lines.append(f"storylines_completed: {metrics.get('storylines_completed')}")
        lines.append(f"total_area_clears: {metrics.get('total_area_clears')}")
    goals = score.get("goal", {})
    for name, status in goals.items():
        lines.append(f"goal {name}: {json.dumps(status, sort_keys=True)}")
    if reward_obj.get("budgetExceeded"):
        lines.append("result: failed tick budget; see reward.json for full metrics")
    elif reward_obj.get("goalAchieved") is False:
        lines.append("result: accepted partial; see goalFailed for missing goals")
    elif reward_obj.get("goalAchieved") is True:
        lines.append("result: goal complete")
    else:
        lines.append("result: reward accepted")
    return "\n".join(lines) + "\n"


def verification_outcome(*, accepted: bool, goal_achieved: bool | None) -> str:
    if not accepted:
        return "rejected"
    if goal_achieved is False:
        return "partial"
    if goal_achieved is True:
        return "success"
    return "accepted"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or score an Arcane Lab agent attempt.")
    parser.add_argument("--state", default="logs/verifier/state.json", help="State file to load or write.")
    parser.add_argument("--script", help="Optional command script to run before scoring.")
    parser.add_argument("--new", action="store_true", help="Start from a fresh state.")
    parser.add_argument("--out-dir", default="logs/verifier", help="Directory for reward and tracking output.")
    parser.add_argument("--goal-storyline", help="Award goal bonus for completing a storyline id.")
    parser.add_argument("--goal-area", help="Award goal bonus for clearing an area id.")
    parser.add_argument("--goal-area-clears", type=int, default=1)
    parser.add_argument("--goal-area-progress", help="Award goal bonus for area progress as AREA:STEPS.")
    parser.add_argument("--goal-recipe", help="Award goal bonus for owning a recipe id.")
    parser.add_argument("--goal-recipe-count", type=int, default=1)
    parser.add_argument("--goal-assignment", help="Award goal bonus for assigning wizards to a spell id.")
    parser.add_argument("--goal-assignment-count", type=int, default=1)
    parser.add_argument("--goal-wizards", type=int, help="Award goal bonus for hiring at least this many wizards.")
    parser.add_argument("--goal-retirements", type=int, help="Award goal bonus for at least this many retirements.")
    parser.add_argument("--goal-insight", type=int, help="Award goal bonus for at least this much insight.")
    parser.add_argument("--goal-run", type=int, help="Award goal bonus for reaching at least this run number.")
    parser.add_argument("--goal-unlocked-area", action="append", help="Award goal bonus for each unlocked area id.")
    parser.add_argument("--tick-budget", type=int, help="Fail the reward if lifetime game ticks exceed this budget.")
    parser.add_argument("--lifetime-tick-budget", type=int, help="Explicit alias for a lifetime tick budget.")
    parser.add_argument("--soft-stop-tick", type=int, help="Score advisory lifetime tick discipline without zeroing reward.")
    parser.add_argument(
        "--soft-stop-scoring",
        default="binary",
        help="Soft-stop scoring policy: binary or linear_to_hard_budget.",
    )
    parser.add_argument("--per-run-tick-budget", type=int, help="Fail the reward if final current-run tick exceeds this budget.")
    args = parser.parse_args()

    sdk = ArcaneLabSDK(state_path=args.state, new=args.new, autosave=False)
    if args.script:
        sdk.run_script(args.script)
    sdk.save(args.state)

    goal = parse_goal(args)
    reward = sdk.score(goal or None)
    metrics = sdk.metrics()
    final_lifetime_tick_budget = args.lifetime_tick_budget
    if final_lifetime_tick_budget is None:
        final_lifetime_tick_budget = args.tick_budget
    lifetime_tick_budget_exceeded = (
        final_lifetime_tick_budget is not None
        and int(metrics["lifetime_tick"]) > int(final_lifetime_tick_budget)
    )
    per_run_tick_budget_exceeded = (
        args.per_run_tick_budget is not None
        and int(metrics["tick"]) > int(args.per_run_tick_budget)
    )
    budget_exceeded = lifetime_tick_budget_exceeded or per_run_tick_budget_exceeded
    soft_stop_exceeded = (
        args.soft_stop_tick is not None
        and int(metrics["lifetime_tick"]) > int(args.soft_stop_tick)
    )
    soft_stop_overrun = (
        max(0, int(metrics["lifetime_tick"]) - int(args.soft_stop_tick))
        if args.soft_stop_tick is not None
        else None
    )
    soft_stop_scoring = normalize_soft_stop_scoring(args.soft_stop_scoring)
    soft_stop_score_value = soft_stop_score(
        scoring=soft_stop_scoring,
        used=int(metrics["lifetime_tick"]),
        soft_stop=args.soft_stop_tick,
        hard_limit=final_lifetime_tick_budget,
    )

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tracking_path = sdk.export_tracking(out_dir / "tracking.json")
    goal_completion = reward.get("goal_completion", {})
    goal_achieved = goal_completion.get("achieved")
    accepted = not budget_exceeded
    reward_obj = {
        "reward": reward["reward"],
        "accepted": accepted,
        "outcome": verification_outcome(accepted=accepted, goal_achieved=goal_achieved),
        "goalAchieved": goal_achieved,
        "goalCompletion": {
            "achieved": goal_achieved,
            "achievedCount": goal_completion.get("achieved_count"),
            "total": goal_completion.get("total"),
            "failed": goal_completion.get("failed", []),
        },
        "score": reward,
        "tickBudget": final_lifetime_tick_budget,
        "tickBudgetType": "lifetime",
        "tickBudgetUsed": metrics["lifetime_tick"],
        "tickBudgetExceeded": lifetime_tick_budget_exceeded,
        "budgetExceeded": budget_exceeded,
        "lifetimeTickBudget": final_lifetime_tick_budget,
        "lifetimeTickBudgetUsed": metrics["lifetime_tick"],
        "lifetimeTickBudgetExceeded": lifetime_tick_budget_exceeded,
        "softStopTick": args.soft_stop_tick,
        "softStopUsed": metrics["lifetime_tick"],
        "softStopExceeded": soft_stop_exceeded,
        "softStopOverrun": soft_stop_overrun,
        "softStopScoring": soft_stop_scoring,
        "softStopScore": soft_stop_score_value,
        "complianceScore": soft_stop_score_value,
        "compliance": {
            "softStop": {
                "used": metrics["lifetime_tick"],
                "limit": args.soft_stop_tick,
                "exceeded": soft_stop_exceeded,
                "overrun": soft_stop_overrun,
                "scoring": soft_stop_scoring,
                "score": soft_stop_score_value,
            }
        },
        "perRunTickBudget": args.per_run_tick_budget,
        "perRunTickBudgetUsed": metrics["tick"],
        "perRunTickBudgetExceeded": per_run_tick_budget_exceeded,
        "statePath": str(resolve(args.state)),
        "trackingPath": str(tracking_path),
    }
    (out_dir / "reward.json").write_text(
        json.dumps(reward_obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "reward.txt").write_text(str(reward["reward"]), encoding="utf-8")
    (out_dir / "summary.txt").write_text(reward_summary(reward_obj), encoding="utf-8")

    print("__REWARD_JSON_START__")
    print(json.dumps(reward_obj, sort_keys=True))
    print("__REWARD_JSON_END__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
