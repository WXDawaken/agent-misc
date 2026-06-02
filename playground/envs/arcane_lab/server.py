from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
from pathlib import Path
from typing import Any

import game
from sdk import ArcaneLabSDK


ROOT = Path(__file__).resolve().parent
PLAYGROUND_ROOT = ROOT.parents[1] if ROOT.name == "arcane_lab" and ROOT.parent.name == "envs" else ROOT
DEFAULT_DATA_DIR = PLAYGROUND_ROOT / "logs" / "server" / "games"
DEFAULT_TOKEN_PATH = PLAYGROUND_ROOT / "logs" / "server" / "auth_tokens.json"
ENV_ID = "arcane_lab"
DISPLAY_NAME = "Arcane Lab"

if str(PLAYGROUND_ROOT) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND_ROOT))

from server_core import (  # noqa: E402
    AuthError,
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

    def mint(
        self,
        *,
        task_id: str,
        env_id: str = ENV_ID,
        track: str | None = None,
        max_new_games: int = 1,
        ttl_seconds: int = 3600,
        goal: dict[str, Any] | None = None,
        tick_budget: int | None = None,
        soft_stop_tick: int | None = None,
        soft_stop_scoring: str | None = None,
        per_run_tick_budget: int | None = None,
        token_role: str = "official",
        official: bool = True,
        scoring: str | None = None,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> dict[str, Any]:
        resolved_crit_mode = game.resolve_crit_mode(crit_mode)
        resolved_crit_seed = crit_seed
        if resolved_crit_mode == "random" and not resolved_crit_seed:
            resolved_crit_seed = secrets.token_urlsafe(24)
        crit_seed_hash = (
            hashlib.sha256(str(resolved_crit_seed).encode("utf-8")).hexdigest()[:12]
            if resolved_crit_seed
            else None
        )
        return super().mint(
            task_id=task_id,
            env_id=env_id,
            track=track,
            max_new_games=max_new_games,
            ttl_seconds=ttl_seconds,
            goal=goal,
            tick_budget=tick_budget,
            soft_stop_tick=soft_stop_tick,
            soft_stop_scoring=soft_stop_scoring,
            per_run_tick_budget=per_run_tick_budget,
            token_role=token_role,
            official=official,
            scoring=scoring,
            extra_record={
                "crit_mode": resolved_crit_mode,
                "crit_seed": resolved_crit_seed,
                "crit_seed_hash": crit_seed_hash,
                "crit_charge_bonus": crit_charge_bonus,
                "crit_random_chance": crit_random_chance,
                "crit_random_bonus": crit_random_bonus,
            },
        )

    def _public_policy(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "crit_mode": record.get("crit_mode", "charge"),
            "crit_seed_hash": record.get("crit_seed_hash"),
            "crit_charge_bonus": record.get("crit_charge_bonus"),
            "crit_random_chance": record.get("crit_random_chance"),
            "crit_random_bonus": record.get("crit_random_bonus"),
        }

    def _game_private_policy(self, record: dict[str, Any]) -> dict[str, Any]:
        return {"crit_seed": record.get("crit_seed")}


class ArcaneLabAdapter:
    env_id = ENV_ID
    display_name = DISPLAY_NAME

    def new_session(
        self,
        state_path: Path,
        *,
        token_info: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ArcaneLabSDK:
        options = options or {}
        game_crit_mode = token_info.get("crit_mode") if token_info else options.get("crit_mode")
        game_crit_seed = token_info.get("crit_seed") if token_info else options.get("crit_seed")
        game_crit_charge_bonus = token_info.get("crit_charge_bonus") if token_info else options.get("crit_charge_bonus")
        game_crit_random_chance = token_info.get("crit_random_chance") if token_info else options.get("crit_random_chance")
        game_crit_random_bonus = token_info.get("crit_random_bonus") if token_info else options.get("crit_random_bonus")
        return ArcaneLabSDK(
            state_path=state_path,
            new=True,
            autosave=True,
            crit_mode=game_crit_mode,
            crit_seed=game_crit_seed,
            crit_charge_bonus=game_crit_charge_bonus,
            crit_random_chance=game_crit_random_chance,
            crit_random_bonus=game_crit_random_bonus,
        )

    def load_session(self, state_path: Path) -> ArcaneLabSDK:
        return ArcaneLabSDK(state_path=state_path, autosave=True)

    def save_session(self, session: ArcaneLabSDK) -> None:
        session.save()

    def observe(self, session: ArcaneLabSDK, *, include_text: bool = True) -> dict[str, Any]:
        return session.observe(include_text=include_text)

    def step(self, session: ArcaneLabSDK, command: str) -> StepOutcome:
        result = session.step(command)
        return StepOutcome(output=result.output, reward=result.reward, done=result.done)

    def list_available(self, session: ArcaneLabSDK, kind: str) -> str:
        return session.list_available(kind)

    def score(self, session: ArcaneLabSDK, goal: dict[str, Any] | None = None) -> dict[str, Any]:
        return session.score(goal)

    def metrics(self, session: ArcaneLabSDK) -> dict[str, Any]:
        return session.metrics()

    def session_metadata(self, session: ArcaneLabSDK) -> dict[str, Any]:
        return {"crit": game.crit_public_state(session.state, session.data)}

    def summary_fields(self, observation: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
        return {
            "run": observation.get("run"),
            "tick": observation.get("tick"),
            "lifetime_tick": observation.get("lifetime_tick"),
            "retirements": observation.get("retirements"),
            "insight": observation.get("insight"),
        }

    def trajectory_metrics(self, trajectory: dict[str, Any]) -> dict[str, Any]:
        entries = trajectory.get("entries", [])
        run_ticks: dict[str, int] = {}
        failed_commands = 0
        retirement_ticks: list[dict[str, int]] = []
        previous_observation: dict[str, Any] | None = None
        for entry in entries:
            observation = entry.get("observation", {})
            run = observation.get("run")
            tick = observation.get("tick")
            if run is not None and tick is not None:
                run_key = str(run)
                run_ticks[run_key] = max(run_ticks.get(run_key, 0), int(tick))
            output = str(entry.get("output", "")).lower()
            if entry.get("command") not in {"__init__", "__load__"} and any(
                marker in output
                for marker in ("fail", "failed", "not enough", "cannot", "unknown", "stopped")
            ):
                failed_commands += 1
            if entry.get("command") == "retire" and previous_observation:
                retirement_ticks.append({
                    "run": int(previous_observation.get("run", 0)),
                    "tick": int(previous_observation.get("tick", 0)),
                    "lifetime_tick": int(previous_observation.get("lifetime_tick", previous_observation.get("tick", 0))),
                })
            previous_observation = observation
        max_run_tick = max(run_ticks.values(), default=0)
        final_observation = entries[-1].get("observation", {}) if entries else {}
        return {
            "command_count": max(0, len(entries) - 1),
            "failed_command_count": failed_commands,
            "run_ticks": run_ticks,
            "max_run_tick": max_run_tick,
            "final_run_tick": int(final_observation.get("tick", 0) or 0),
            "final_lifetime_tick": int(final_observation.get("lifetime_tick", final_observation.get("tick", 0)) or 0),
            "retirement_ticks": retirement_ticks,
            "post_retire_ticks": int(final_observation.get("tick", 0) or 0) if int(final_observation.get("retirements", 0) or 0) else None,
        }

    def budget_policy(self) -> dict[str, Any]:
        return {
            "primary_metric": "lifetime_tick",
            "primary_token_key": "tick_budget",
            "primary_goal_keys": ("lifetime_tick_budget", "tick_budget"),
            "primary_goal_emit_key": "tick_budget",
            "soft_stop_metric": "lifetime_tick",
            "soft_stop_token_key": "soft_stop_tick",
            "soft_stop_goal_keys": ("soft_stop_tick",),
            "secondary_metric": "tick",
            "secondary_token_key": "per_run_tick_budget",
            "secondary_goal_keys": ("per_run_tick_budget",),
            "secondary_goal_emit_key": "per_run_tick_budget",
            "legacy_tick_budget_type": "lifetime",
        }


class GameStore(PersistedGameStore):
    def __init__(self, games_root: Path = DEFAULT_DATA_DIR) -> None:
        super().__init__(games_root, ArcaneLabAdapter())

    def create_game(
        self,
        label: str | None = None,
        *,
        token_info: dict[str, Any] | None = None,
        game_id: str | None = None,
        crit_mode: str | None = None,
        crit_seed: str | None = None,
        crit_charge_bonus: float | None = None,
        crit_random_chance: float | None = None,
        crit_random_bonus: float | None = None,
    ) -> dict[str, Any]:
        return super().create_game(
            label=label,
            token_info=token_info,
            game_id=game_id,
            crit_mode=crit_mode,
            crit_seed=crit_seed,
            crit_charge_bonus=crit_charge_bonus,
            crit_random_chance=crit_random_chance,
            crit_random_bonus=crit_random_bonus,
        )


STATIC_DIR = ROOT / "static"
INDEX_HTML_PATH = STATIC_DIR / "replay.html"


def load_index_html() -> str:
    return INDEX_HTML_PATH.read_text(encoding="utf-8")


def _create_game_options(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "crit_mode": payload.get("crit_mode") or payload.get("critMode"),
        "crit_seed": payload.get("crit_seed") or payload.get("critSeed"),
        "crit_charge_bonus": payload.get("crit_charge_bonus") or payload.get("critChargeBonus"),
        "crit_random_chance": payload.get("crit_random_chance") or payload.get("critRandomChance"),
        "crit_random_bonus": payload.get("crit_random_bonus") or payload.get("critRandomBonus"),
    }


SERVER_SPEC = EnvironmentServerSpec(
    env_id=ENV_ID,
    display_name=DISPLAY_NAME,
    default_data_dir=DEFAULT_DATA_DIR,
    default_token_path=DEFAULT_TOKEN_PATH,
    store_factory=GameStore,
    token_registry_factory=TokenRegistry,
    load_index_html=load_index_html,
    server_version="ArcaneLabServer/0.1",
    token_headers=("X-Arcane-Lab-Token", "X-Playground-Token"),
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
    parser = argparse.ArgumentParser(description="Mint an Arcane Lab server auth token")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--track", help="Optional track id recorded in the official token policy.")
    parser.add_argument("--max-new-games", type=int, default=1)
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    parser.add_argument("--goal-json", help="Optional JSON goal used by /verify when no goal is supplied.")
    parser.add_argument("--tick-budget", type=int, help="Lifetime tick budget enforced by official verification.")
    parser.add_argument("--soft-stop-tick", type=int, help="Advisory lifetime tick target scored separately from hard acceptance.")
    parser.add_argument(
        "--soft-stop-scoring",
        default="binary",
        help="Soft-stop scoring policy recorded on the token: binary or linear_to_hard_budget.",
    )
    parser.add_argument("--per-run-tick-budget", type=int, help="Optional current-run tick budget enforced by official verification.")
    parser.add_argument("--token-role", default="official", help="Role recorded on token-created games.")
    parser.add_argument("--scoring", default="single", help="Scoring policy label recorded with the token.")
    official_group = parser.add_mutually_exclusive_group()
    official_group.add_argument("--official", dest="official", action="store_true", help="Token-created games are verifiable official games.")
    official_group.add_argument("--unofficial", dest="official", action="store_false", help="Token-created games are non-official practice games.")
    parser.set_defaults(official=True)
    parser.add_argument(
        "--crit-mode",
        choices=sorted(game.CRIT_MODE_ALIASES),
        default="charge",
        help="Official crit mode for games created with this token.",
    )
    parser.add_argument("--crit-seed", help="Optional server-side seed for random crit mode.")
    parser.add_argument("--crit-charge-bonus", type=float, help="Base charge-mode attack bonus at full focus.")
    parser.add_argument("--crit-random-chance", type=float, help="Base random-mode crit chance before buffs/equipment.")
    parser.add_argument("--crit-random-bonus", type=float, help="Base random-mode attack bonus on crit.")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_PATH)
    parser.add_argument(
        "--env",
        action="store_true",
        help="Print PowerShell environment assignments instead of JSON.",
    )
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    args = parser.parse_args(argv)

    goal = None
    if args.goal_json:
        goal = json.loads(args.goal_json)
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
        crit_mode=args.crit_mode,
        crit_seed=args.crit_seed,
        crit_charge_bonus=args.crit_charge_bonus,
        crit_random_chance=args.crit_random_chance,
        crit_random_bonus=args.crit_random_bonus,
    )
    if args.env:
        token_env = "ARCANE_LAB_PRACTICE_AUTH_TOKEN" if args.token_role == "practice" else "ARCANE_LAB_AUTH_TOKEN"
        print(f"$env:ARCANE_LAB_SERVER_URL = \"{args.server_url}\"")
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
