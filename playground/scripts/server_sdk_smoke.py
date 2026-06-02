from __future__ import annotations

import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdk import ArcaneLabServerSDK  # noqa: E402
from server import GameStore, TokenRegistry, make_handler  # noqa: E402


def main() -> int:
    games_root = ROOT / "logs" / "server_sdk_smoke" / "games"
    token_path = ROOT / "logs" / "server_sdk_smoke" / "auth_tokens.json"
    existing_game_dirs = {
        path.name
        for path in games_root.iterdir()
        if path.is_dir()
    } if games_root.exists() else set()
    store = GameStore(games_root)
    registry = TokenRegistry(token_path)
    token = registry.mint(
        task_id="server-sdk-smoke",
        max_new_games=1,
        ttl_seconds=600,
        goal={"storyline": "field_notes"},
        tick_budget=1,
        soft_stop_tick=0,
    )["token"]
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(store, token_registry=registry, require_token=True),
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    old_env = {
        "ARCANE_LAB_SERVER_URL": os.environ.get("ARCANE_LAB_SERVER_URL"),
        "ARCANE_LAB_AUTH_TOKEN": os.environ.get("ARCANE_LAB_AUTH_TOKEN"),
        "ARCANE_LAB_CRIT_MODE": os.environ.get("ARCANE_LAB_CRIT_MODE"),
    }
    try:
        host, port = httpd.server_address
        base_url = f"http://{host}:{port}"
        os.environ["ARCANE_LAB_SERVER_URL"] = base_url
        os.environ["ARCANE_LAB_AUTH_TOKEN"] = token
        os.environ["ARCANE_LAB_CRIT_MODE"] = "random"
        lab = ArcaneLabServerSDK(new=True, label="server-sdk-smoke")
        result = lab.step("study ember 1")
        if result.observation["tick"] != 1:
            raise AssertionError(f"expected tick 1, got {result.observation['tick']}")
        spells = lab.list_available("spells")
        if "fire_lance" not in spells and "shape_pebble" not in spells:
            raise AssertionError("server SDK list_available did not return spell text")
        score = lab.score()
        if "reward" not in score:
            raise AssertionError("server SDK score missing reward")
        goal_score = lab.score({"storyline": "field_notes"})
        if "goal" not in goal_score:
            raise AssertionError("server SDK goal score missing goal details")
        verification = lab.verify({"recipe": "focus_lens"}, tick_budget=5)
        if "trajectory_hash" not in verification:
            raise AssertionError("server SDK verify missing trajectory hash")
        if verification["tickBudget"] != 1:
            raise AssertionError(f"expected token tick budget 1, got {verification['tickBudget']}")
        if verification.get("tickBudgetType") != "lifetime":
            raise AssertionError(f"expected lifetime tick budget type, got {verification.get('tickBudgetType')}")
        if verification.get("tickBudgetUsed") != 1:
            raise AssertionError(f"expected lifetime tick budget used 1, got {verification.get('tickBudgetUsed')}")
        if verification.get("perRunTickBudgetUsed") != 1:
            raise AssertionError(f"expected per-run tick budget used 1, got {verification.get('perRunTickBudgetUsed')}")
        if verification.get("softStopTick") != 0:
            raise AssertionError(f"expected token soft stop 0, got {verification.get('softStopTick')}")
        if not verification.get("softStopExceeded"):
            raise AssertionError(f"expected soft stop to be exceeded, got {verification}")
        if verification.get("softStopScore") != 0:
            raise AssertionError(f"expected soft stop score 0, got {verification.get('softStopScore')}")
        if not verification.get("accepted"):
            raise AssertionError(f"soft stop should not reject a hard-budget accepted run: {verification}")
        if verification.get("goalAchieved") is not False:
            raise AssertionError(f"merged smoke goal should be incomplete but explicit: {verification}")
        if verification.get("outcome") != "partial":
            raise AssertionError(f"expected accepted-but-partial outcome, got {verification.get('outcome')}: {verification}")
        failed_goals = set(verification.get("goalCompletion", {}).get("failed", []))
        if not {"storyline:field_notes", "recipe:focus_lens"}.issubset(failed_goals):
            raise AssertionError(f"expected failed goal details, got {verification.get('goalCompletion')}")
        policy = verification.get("policy", {})
        if policy.get("tick_budget_source") != "token":
            raise AssertionError(f"expected token tick budget policy, got {policy}")
        if policy.get("soft_stop_tick_source") != "token":
            raise AssertionError(f"expected token soft stop policy, got {policy}")
        if not policy.get("request_tick_budget_ignored"):
            raise AssertionError(f"expected request tick budget to be ignored, got {policy}")
        if not policy.get("tick_budget_conflict"):
            raise AssertionError(f"expected request/token tick budget conflict, got {policy}")
        if verification["goal"].get("storyline") != "field_notes":
            raise AssertionError(f"token goal was not merged into verification goal: {verification['goal']}")
        if verification["goal"].get("recipe") != "focus_lens":
            raise AssertionError(f"request goal was not preserved in verification goal: {verification['goal']}")
        try:
            lab.step("study ember 1")
        except RuntimeError as exc:
            if "already submitted" not in str(exc):
                raise AssertionError(f"unexpected post-verify step failure: {exc}") from exc
        else:
            raise AssertionError("official game accepted commands after verify submission")
        trajectory = lab.trajectory()
        if len(trajectory["entries"]) != 2:
            raise AssertionError(f"expected 2 entries, got {len(trajectory['entries'])}")
        game_id = lab.game_id
        if not game_id:
            raise AssertionError("server SDK did not retain game_id")
        resumed = ArcaneLabServerSDK()
        if resumed.game_id != game_id:
            raise AssertionError(f"server SDK did not resume token game: {resumed.game_id} != {game_id}")
        trajectory_path = games_root / game_id / "trajectory.json"
        saved = json.loads(trajectory_path.read_text(encoding="utf-8"))
        if saved["entries"][-1]["command"] != "study ember 1":
            raise AssertionError("server trajectory did not persist SDK command")
        verification_path = games_root / game_id / "verification.json"
        if not verification_path.exists():
            raise AssertionError("server verification.json was not written")
        extra = ArcaneLabServerSDK(new=True, label="server-sdk-smoke-extra")
        if extra.game_id != game_id:
            raise AssertionError(
                f"token max_new_games created a second game: {extra.game_id} != {game_id}"
            )
        new_game_dirs = {
            path.name
            for path in games_root.iterdir()
            if path.is_dir()
        } - existing_game_dirs
        if new_game_dirs != {game_id}:
            raise AssertionError(f"expected only one new token game, got {sorted(new_game_dirs)}")
        print(f"ok {game_id} {trajectory_path}")
    finally:
        for name, value in old_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
