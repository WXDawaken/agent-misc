from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "ledger_tower" and ROOT.parent.name == "envs" else ROOT
DEFAULT_DATA_DIR = PLAYGROUND_ROOT / "logs" / "server" / "games"
DEFAULT_TOKEN_PATH = PLAYGROUND_ROOT / "logs" / "server" / "auth_tokens_ledger_tower.json"
ENV_ID = "ledger_tower"
DISPLAY_NAME = "Ledger Tower"

if str(PLAYGROUND_ROOT) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND_ROOT))

from envs.ledger_tower import game  # noqa: E402
from envs.ledger_tower.sdk import LedgerTowerSDK  # noqa: E402

from server_core import (  # noqa: E402
    EnvironmentServerSpec,
    PersistedGameStore,
    StepOutcome,
    TokenRegistryBase,
    make_handler as make_core_handler,
    serve_main as serve_core_main,
)


class TokenRegistry(TokenRegistryBase):
    def __init__(self, path: Path = DEFAULT_TOKEN_PATH) -> None:
        super().__init__(path, env_id=ENV_ID)

    def _public_policy(self, record: dict[str, Any]) -> dict[str, Any]:
        policy: dict[str, Any] = {}
        if record.get("data_path"):
            policy["data_path"] = record["data_path"]
        return policy

    def _game_private_policy(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._public_policy(record)


class LedgerTowerAdapter:
    env_id = ENV_ID
    display_name = DISPLAY_NAME

    def new_session(
        self,
        state_path: Path,
        *,
        token_info: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> LedgerTowerSDK:
        budget = {}
        if token_info:
            if token_info.get("tick_budget") is not None:
                budget["limit"] = int(token_info["tick_budget"])
            if token_info.get("soft_stop_tick") is not None:
                budget["soft_stop"] = int(token_info["soft_stop_tick"])
        options = options or {}
        seed = options.get("seed")
        data_path = options.get("data_path")
        if token_info and token_info.get("data_path"):
            data_path = token_info["data_path"]
        return LedgerTowerSDK(
            state_path=state_path,
            new=True,
            autosave=True,
            seed=seed,
            budget=budget,
            data_path=data_path,
        )

    def load_session(self, state_path: Path) -> LedgerTowerSDK:
        return LedgerTowerSDK(state_path=state_path, autosave=True)

    def save_session(self, session: LedgerTowerSDK) -> None:
        session.save()

    def observe(self, session: LedgerTowerSDK, *, include_text: bool = True) -> dict[str, Any]:
        return session.observe(include_text=include_text)

    def step(self, session: LedgerTowerSDK, command: str) -> StepOutcome:
        result = session.step(command)
        return StepOutcome(output=result.output, reward=result.reward, done=result.done)

    def list_available(self, session: LedgerTowerSDK, kind: str) -> str:
        return session.list_available(kind)

    def score(self, session: LedgerTowerSDK, goal: dict[str, Any] | None = None) -> dict[str, Any]:
        return session.score(goal)

    def metrics(self, session: LedgerTowerSDK) -> dict[str, Any]:
        return session.metrics()

    def session_metadata(self, session: LedgerTowerSDK) -> dict[str, Any]:
        return {
            "seed": session.state.get("seed"),
            "variant": session.state.get("variant"),
            "data_path": session.state.get("data_path"),
        }

    def summary_fields(self, observation: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
        state = observation.get("state", {})
        return {
            "moves": observation.get("moves"),
            "floor": observation.get("floor"),
            "hp": state.get("hp"),
            "atk": state.get("atk"),
            "def": state.get("def"),
            "gold": state.get("gold"),
            "victory": state.get("victory"),
        }

    def trajectory_metrics(self, trajectory: dict[str, Any]) -> dict[str, Any]:
        entries = trajectory.get("entries", [])
        failed_commands = 0
        for entry in entries:
            command = entry.get("command")
            if command in {"__init__", "__load__"}:
                continue
            output = str(entry.get("output", "")).lower()
            if any(marker in output for marker in ("blocked", "not enough", "cannot", "rejected", "unknown", "requires")):
                failed_commands += 1
        final_observation = entries[-1].get("observation", {}) if entries else {}
        final_state = final_observation.get("state", {})
        return {
            "command_count": max(0, len(entries) - 1),
            "failed_command_count": failed_commands,
            "final_moves": int(final_observation.get("moves", 0) or 0),
            "final_floor": final_observation.get("floor"),
            "final_hp": int(final_state.get("hp", 0) or 0),
            "victory": bool(final_state.get("victory")),
        }

    def budget_policy(self) -> dict[str, Any]:
        return {
            "primary_metric": "moves",
            "primary_token_key": "tick_budget",
            "primary_goal_keys": ("moves_max", "tick_budget", "lifetime_tick_budget"),
            "primary_goal_emit_key": "tick_budget",
            "soft_stop_metric": "moves",
            "soft_stop_token_key": "soft_stop_tick",
            "soft_stop_goal_keys": ("soft_stop_tick",),
            "secondary_metric": None,
            "secondary_token_key": "per_run_tick_budget",
            "secondary_goal_keys": (),
            "secondary_goal_emit_key": "per_run_tick_budget",
            "legacy_tick_budget_type": "moves",
        }


class GameStore(PersistedGameStore):
    def __init__(self, games_root: Path = DEFAULT_DATA_DIR) -> None:
        super().__init__(games_root, LedgerTowerAdapter())

    def create_game(
        self,
        label: str | None = None,
        *,
        token_info: dict[str, Any] | None = None,
        game_id: str | None = None,
        seed: str | None = None,
        data_path: str | None = None,
    ) -> dict[str, Any]:
        return super().create_game(
            label=label,
            token_info=token_info,
            game_id=game_id,
            seed=seed,
            data_path=data_path,
        )


STATIC_DIR = ROOT / "static"
INDEX_HTML_PATH = STATIC_DIR / "replay.html"


def load_index_html() -> str:
    return INDEX_HTML_PATH.read_text(encoding="utf-8")


def _create_game_options(payload: dict[str, Any]) -> dict[str, Any]:
    return {"seed": payload.get("seed"), "data_path": payload.get("data_path")}


SERVER_SPEC = EnvironmentServerSpec(
    env_id=ENV_ID,
    display_name=DISPLAY_NAME,
    default_data_dir=DEFAULT_DATA_DIR,
    default_token_path=DEFAULT_TOKEN_PATH,
    store_factory=GameStore,
    token_registry_factory=TokenRegistry,
    load_index_html=load_index_html,
    server_version="LedgerTowerServer/0.1",
    token_headers=("X-Ledger-Tower-Token", "X-Playground-Token"),
    create_game_options=_create_game_options,
)


def make_handler(
    store: GameStore,
    *,
    token_registry: TokenRegistry | None = None,
    require_token: bool = False,
) -> Any:
    return make_core_handler(
        store,
        spec=SERVER_SPEC,
        token_registry=token_registry,
        require_token=require_token,
    )


def serve_main(argv: list[str] | None = None) -> int:
    return serve_core_main(SERVER_SPEC, argv)


def mint_token_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mint a Ledger Tower server auth token")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--track", help="Optional track id recorded in the official token policy.")
    parser.add_argument("--max-new-games", type=int, default=1)
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    parser.add_argument("--goal-json", help="Optional JSON goal used by /verify when no goal is supplied.")
    parser.add_argument("--tick-budget", type=int, help="Move budget enforced by official verification.")
    parser.add_argument("--soft-stop-tick", type=int, help="Advisory move target scored separately from hard acceptance.")
    parser.add_argument(
        "--soft-stop-scoring",
        default="binary",
        help="Soft-stop scoring policy recorded on the token: binary or linear_to_hard_budget.",
    )
    parser.add_argument("--per-run-tick-budget", type=int, help="Accepted for shared runner compatibility; ignored.")
    parser.add_argument("--token-role", default="official", help="Role recorded on token-created games.")
    parser.add_argument("--scoring", default="single", help="Scoring policy label recorded with the token.")
    parser.add_argument("--data-path", help="Optional alternate Ledger Tower data JSON for token-created games.")
    official_group = parser.add_mutually_exclusive_group()
    official_group.add_argument("--official", dest="official", action="store_true", help="Token-created games are verifiable official games.")
    official_group.add_argument("--unofficial", dest="official", action="store_false", help="Token-created games are non-official practice games.")
    parser.set_defaults(official=True)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_PATH)
    parser.add_argument(
        "--env",
        action="store_true",
        help="Print PowerShell environment assignments instead of JSON.",
    )
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    args = parser.parse_args(argv)

    goal = json.loads(args.goal_json) if args.goal_json else None
    registry = TokenRegistry(args.token_file)
    token = registry.mint(
        task_id=args.task_id,
        env_id=ENV_ID,
        track=args.track,
        max_new_games=args.max_new_games,
        ttl_seconds=args.ttl_seconds,
        goal=goal,
        tick_budget=args.tick_budget,
        soft_stop_tick=args.soft_stop_tick,
        soft_stop_scoring=args.soft_stop_scoring,
        per_run_tick_budget=args.per_run_tick_budget,
        token_role=args.token_role,
        official=args.official,
        scoring=args.scoring,
        extra_record={"data_path": args.data_path} if args.data_path else None,
    )
    if args.env:
        token_env = "LEDGER_TOWER_PRACTICE_AUTH_TOKEN" if args.token_role == "practice" else "LEDGER_TOWER_AUTH_TOKEN"
        print(f"$env:LEDGER_TOWER_SERVER_URL = \"{args.server_url}\"")
        print(f"$env:{token_env} = \"{token['token']}\"")
    else:
        print(json.dumps(token, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "mint-token":
        return mint_token_main(args[1:])
    return serve_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
