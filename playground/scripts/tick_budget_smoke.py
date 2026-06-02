from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdk import ArcaneLabSDK  # noqa: E402


def main() -> int:
    lab = ArcaneLabSDK(new=True)
    lab.step("tick 3")
    lab.state["retirement_unlocked"] = True
    lab.step("retire")
    metrics = lab.metrics()
    if metrics["tick"] != 0:
        raise AssertionError(f"expected current run tick 0 after retire, got {metrics['tick']}")
    if metrics["lifetime_tick"] != 3:
        raise AssertionError(f"expected lifetime tick 3 after retire, got {metrics['lifetime_tick']}")

    lifetime_fail = lab.score({"tick_budget": 2})
    if lifetime_fail["reward"] != 0 or lifetime_fail["goal"]["tick_budget"]["achieved"]:
        raise AssertionError(f"expected legacy tick_budget to enforce lifetime ticks, got {lifetime_fail}")

    per_run_pass = lab.score({"per_run_tick_budget": 0})
    if not per_run_pass["goal"]["per_run_tick_budget"]["achieved"]:
        raise AssertionError(f"expected per-run budget to use current run tick, got {per_run_pass}")
    if per_run_pass["reward"] <= 0:
        raise AssertionError(f"expected per-run pass to preserve reward, got {per_run_pass}")

    both_pass = lab.score({"lifetime_tick_budget": 3, "per_run_tick_budget": 0})
    if both_pass["reward"] <= 0:
        raise AssertionError(f"expected exact lifetime/per-run budgets to pass, got {both_pass}")

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
