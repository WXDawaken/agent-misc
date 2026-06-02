from __future__ import annotations

import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import game  # noqa: E402
from sdk import ArcaneLabSDK, ArcaneLabServerSDK  # noqa: E402
from server import GameStore, TokenRegistry, make_handler  # noqa: E402


def check_charge_mode() -> None:
    lab = ArcaneLabSDK(new=True)
    lab.run([
        "study ember 4",
        "study stone 4",
        "cast fire_lance",
        "explore training_yard 3",
    ])
    crit = lab.observe(include_text=False)["crit"]
    if crit["mode"] != "charge":
        raise AssertionError(f"expected charge crit mode, got {crit}")
    if crit["charge"] != 3:
        raise AssertionError(f"expected full charge before deterministic crit, got {crit}")
    result = lab.step("explore training_yard 1")
    last = result.observation["crit"]["last"]
    if not last.get("triggered"):
        raise AssertionError(f"expected deterministic charge crit, got {last}")
    if result.observation["crit"]["charge"] != 0:
        raise AssertionError(f"expected charge to reset after crit, got {result.observation['crit']}")


def check_random_mode() -> None:
    lab = ArcaneLabSDK(new=True, crit_mode="random", crit_seed="crit-smoke")
    result = lab.step("explore training_yard 1")
    last = result.observation["crit"]["last"]
    if result.observation["crit"]["mode"] != "random":
        raise AssertionError(f"expected random crit mode, got {result.observation['crit']}")
    if last.get("roll_index") != 0 or "roll" not in last:
        raise AssertionError(f"expected recorded first crit roll, got {last}")
    if not last.get("triggered"):
        raise AssertionError(f"expected crit-smoke seed to trigger first roll, got {last}")


def unlock_keen_focus(lab: ArcaneLabSDK) -> None:
    if "quiet_archive" not in lab.state["completed_storylines"]:
        lab.state["completed_storylines"].append("quiet_archive")
    game.ensure_element(lab.state, "mind")
    lab.state["elements"]["mind"]["level"] = 2
    lab.state["mana"] = 999


def check_keen_focus_charge_mode() -> None:
    lab = ArcaneLabSDK(new=True)
    unlock_keen_focus(lab)
    lab.state["elements"]["ember"]["level"] = 5
    lab.state["elements"]["stone"]["level"] = 5
    result = lab.step("cast keen_focus")
    buff = result.observation["buffs"].get("keen_focus", {})
    if buff.get("crit_charge_gain") != 1 or "crit_chance" in buff or "crit_chance_multiplier" in buff:
        raise AssertionError(f"expected charge-only keen_focus buff, got {buff}")
    if result.observation["crit"]["charge_gain"] != 2:
        raise AssertionError(f"expected charge gain 2, got {result.observation['crit']}")
    result = lab.step("explore training_yard 1")
    last = result.observation["crit"]["last"]
    if last.get("charge_gain") != 2 or result.observation["crit"]["charge"] != 2:
        raise AssertionError(f"expected keen_focus to add 2 charge on success, got {last}")


def check_keen_focus_random_mode() -> None:
    lab = ArcaneLabSDK(new=True, crit_mode="random", crit_seed="crit-smoke")
    unlock_keen_focus(lab)
    result = lab.step("cast keen_focus")
    buff = result.observation["buffs"].get("keen_focus", {})
    if buff.get("crit_chance_multiplier") != 0.5 or "crit_chance" in buff or "crit_charge_gain" in buff:
        raise AssertionError(f"expected random-only keen_focus buff, got {buff}")
    crit = result.observation["crit"]
    if abs(crit["random_chance"] - 0.27) > 1e-9:
        raise AssertionError(f"expected 27% effective crit chance, got {crit}")


def check_seer_glass_chance() -> None:
    lab = ArcaneLabSDK(new=True, crit_mode="random", crit_seed="crit-smoke")
    lab.state["equipment"]["seer_glass"] = 1
    crit = lab.observe(include_text=False)["crit"]
    if abs(crit["random_chance"] - 0.38) > 1e-9 or abs(crit["random_bonus"] - 0.20) > 1e-9:
        raise AssertionError(f"expected Seer Glass to raise random crit chance only, got {crit}")
    unlock_keen_focus(lab)
    crit = lab.step("cast keen_focus").observation["crit"]
    if abs(crit["random_chance"] - 0.57) > 1e-9:
        raise AssertionError(f"expected multiplicative Seer Glass + Keen Focus chance, got {crit}")


def check_configurable_base_random_crit() -> None:
    lab = ArcaneLabSDK(
        new=True,
        crit_mode="random",
        crit_seed="crit-smoke",
        crit_random_chance=0.25,
        crit_random_bonus=0.5,
    )
    crit = lab.observe(include_text=False)["crit"]
    if abs(crit["base_random_chance"] - 0.25) > 1e-9 or abs(crit["base_random_bonus"] - 0.5) > 1e-9:
        raise AssertionError(f"expected configurable base random crit, got {crit}")
    next_crit = game.crit_state_for_new_run(lab.state)
    if abs(next_crit["random_chance"] - 0.25) > 1e-9 or abs(next_crit["random_bonus"] - 0.5) > 1e-9:
        raise AssertionError(f"expected crit config to survive retirement reset, got {next_crit}")


def check_server_token_mode() -> None:
    games_root = ROOT / "logs" / "crit_smoke" / "games"
    token_path = ROOT / "logs" / "crit_smoke" / "auth_tokens.json"
    store = GameStore(games_root)
    registry = TokenRegistry(token_path)
    token = registry.mint(
        task_id="crit-smoke",
        max_new_games=1,
        ttl_seconds=600,
        crit_mode="random",
        crit_seed="crit-smoke",
        crit_random_chance=0.25,
        crit_random_bonus=0.5,
    )["token"]
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(store, token_registry=registry, require_token=True),
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address
        base_url = f"http://{host}:{port}"
        lab = ArcaneLabServerSDK(base_url, new=True, label="crit-smoke", auth_token=token)
        crit = lab.observe(include_text=False)["crit"]
        if crit["mode"] != "random":
            raise AssertionError("token crit mode did not reach server-created game")
        if abs(crit["base_random_chance"] - 0.25) > 1e-9 or abs(crit["base_random_bonus"] - 0.5) > 1e-9:
            raise AssertionError(f"token crit config did not reach server-created game: {crit}")
        status = lab.auth_status()
        if "crit_seed" in status:
            raise AssertionError("auth status leaked raw crit seed")
        result = lab.step("explore training_yard 1")
        last = result.observation["crit"]["last"]
        if last.get("roll_index") != 0 or "roll" not in last:
            raise AssertionError(f"server trajectory did not record crit roll, got {last}")
        print(f"ok {lab.game_id}")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def main() -> int:
    check_charge_mode()
    check_random_mode()
    check_keen_focus_charge_mode()
    check_keen_focus_random_mode()
    check_seer_glass_chance()
    check_configurable_base_random_crit()
    check_server_token_mode()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
