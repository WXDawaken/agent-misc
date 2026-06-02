from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server import GameStore  # noqa: E402


def main() -> int:
    games_root = ROOT / "logs" / "server_smoke" / "games"
    store = GameStore(games_root)
    game = store.create_game(label="server-smoke")
    game_id = game["summary"]["id"]
    result = store.step_game(game_id, "study ember 1")
    trajectory_path = games_root / game_id / "trajectory.json"
    state_path = games_root / game_id / "state.json"
    if not trajectory_path.exists():
        raise AssertionError("trajectory.json was not written")
    if not state_path.exists():
        raise AssertionError("state.json was not written")
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    if len(trajectory["entries"]) != 2:
        raise AssertionError(f"expected 2 trajectory entries, got {len(trajectory['entries'])}")
    if trajectory["entries"][-1]["command"] != "study ember 1":
        raise AssertionError("last command was not recorded")
    if result["current"]["tick"] != 1:
        raise AssertionError(f"expected tick 1, got {result['current']['tick']}")
    print(f"ok {game_id} {trajectory_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
