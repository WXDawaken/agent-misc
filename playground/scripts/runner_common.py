from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from typing import Any

from setup_agent_workspace import setup_workspace


DEFAULT_ENVIRONMENT = "arcane_lab"
DEFAULT_HELPER_TIMEOUT_SECONDS = 60


PYTHON_HELPER_GUARD = """\
from __future__ import annotations

import os
import sys
import threading


def _helper_timeout_seconds() -> int:
    raw = os.environ.get("PLAYGROUND_HELPER_TIMEOUT_SECONDS", "60")
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 60


_timeout_seconds = _helper_timeout_seconds()


def _timeout_exit() -> None:
    try:
        sys.stderr.write(
            f"playground helper timeout: Python helper exceeded {_timeout_seconds}s; exiting with code 124\\n"
        )
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(124)


if _timeout_seconds > 0:
    _timer = threading.Timer(_timeout_seconds, _timeout_exit)
    _timer.daemon = True
    _timer.start()
"""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_source_path(source_root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        return path
    candidate = (source_root / path).resolve()
    if candidate.exists():
        return candidate
    fallback = (source_root / "envs" / DEFAULT_ENVIRONMENT / path).resolve()
    if fallback.exists():
        return fallback
    return candidate


def environment_root_for_config(source_root: Path, config_path: Path) -> Path:
    try:
        relative = config_path.resolve().relative_to(source_root.resolve())
    except ValueError:
        return source_root.resolve()
    parts = relative.parts
    if len(parts) >= 2 and parts[0] == "envs":
        return (source_root / "envs" / parts[1]).resolve()
    return source_root.resolve()


def ensure_unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    suffix = 1
    while True:
        candidate = Path(f"{base}_{suffix}")
        if not candidate.exists():
            return candidate
        suffix += 1


def write_python_helper_guard(runner_dir: Path, timeout_seconds: int = DEFAULT_HELPER_TIMEOUT_SECONDS) -> Path:
    guard_dir = runner_dir / "python_guard"
    guard_dir.mkdir(parents=True, exist_ok=True)
    (guard_dir / "sitecustomize.py").write_text(PYTHON_HELPER_GUARD, encoding="utf-8")
    (guard_dir / "README.md").write_text(
        "Runner-provided Python helper guard. Runners add this directory to PYTHONPATH "
        f"so agent helper scripts exit after {timeout_seconds} seconds.\n",
        encoding="utf-8",
    )
    return guard_dir


def _toml_string(value: str) -> str:
    return json.dumps(value)


def write_codex_tool_hook_config(source_root: Path, runner_dir: Path) -> dict[str, str]:
    hook_script = (source_root / "scripts" / "codex_tool_policy_hook.py").resolve()
    hook_log = runner_dir / "codex_hook_events.jsonl"
    command = f'"{sys.executable}" "{hook_script}"'
    config_path = runner_dir / "codex_hook_config.toml"
    config_path.write_text(
        "\n".join(
            [
                "# Audit copy of the runner-provided hook config.",
                "# run_codex_cli_playtest.py passes the same hooks through CLI -c overrides",
                "# so the benchmark does not depend on project-local .codex trust state.",
                "[features]",
                "hooks = true",
                "",
                "[[hooks.PreToolUse]]",
                'matcher = "*"',
                "[[hooks.PreToolUse.hooks]]",
                'type = "command"',
                f"command = {_toml_string(command)}",
                "timeout = 5",
                'statusMessage = "Checking playground tool policy"',
                "",
                "[[hooks.PermissionRequest]]",
                'matcher = "*"',
                "[[hooks.PermissionRequest.hooks]]",
                'type = "command"',
                f"command = {_toml_string(command)}",
                "timeout = 5",
                'statusMessage = "Checking playground permission policy"',
                "",
                "[[hooks.PostToolUse]]",
                'matcher = "*"',
                "[[hooks.PostToolUse.hooks]]",
                'type = "command"',
                f"command = {_toml_string(command)}",
                "timeout = 5",
                'statusMessage = "Recording playground tool result"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "codex_hook_config_path": str(config_path),
        "codex_hook_policy_script": str(hook_script),
        "codex_hook_log_path": str(hook_log),
    }


def safe_fragment(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in value)


MODEL_SHORT_ALIASES = {
    "claude-opus-4-6": "opus46",
    "deepseek-v4-flash": "dsv4f",
    "deepseek-v4-pro": "dsv4p",
    "deepseek-v4-pro[1m]": "dsv4p1m",
    "glm-5.1": "glm51",
    "gpt-5.3-codex-spark": "g53s",
    "gpt-5.4": "g54",
    "gpt-5.5": "g55",
    "hy3-preview-free": "hy3f",
    "kimi-k2.6": "kimi26",
    "mimo-v2.5-pro": "mimo25p",
    "minimax-m2.7": "mmax27",
    "qwen3.6-plus": "qwen36p",
}


TRACK_SHORT_ALIASES = {
    "blind-discovery": "bd",
    "budgeted-prestige": "bp",
    "crit-build-eval": "crit",
    "mechanics-check": "mc",
    "provided-helper-prestige": "php",
    "pure-blind": "pb",
    "route-optimization": "ro",
    "visible-goal": "vg",
    "warmup-fork-prestige": "wfp",
    "high-score-whitebox": "hsw",
    "high-score-token-limited": "hstl",
    "high-score-practice-budgeted": "hspb",
    "high-score-best-of-3": "hsb3",
    "boss-gated-high-score": "bghs",
}


def short_hash(value: str, length: int = 5) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def short_timestamp() -> str:
    return time.strftime("%m%d%H%M")


def short_model_id(model: str) -> str:
    stem = model.replace("\\", "/").split("/")[-1].lower()
    if stem in MODEL_SHORT_ALIASES:
        return MODEL_SHORT_ALIASES[stem]
    parts = [part for part in re.split(r"[^a-z0-9]+", stem) if part]
    if not parts:
        return f"m{short_hash(model)}"
    abbreviation = "".join(part if part[0].isdigit() else part[0] + "".join(ch for ch in part[1:] if ch.isdigit()) for part in parts)
    abbreviation = safe_fragment(abbreviation.lower())[:18]
    if len(abbreviation) < 3:
        abbreviation = safe_fragment(stem)[:18]
    return f"{abbreviation}{short_hash(model, 3)}"


def short_track_id(track: str) -> str:
    stem = track.lower()
    if stem in TRACK_SHORT_ALIASES:
        return TRACK_SHORT_ALIASES[stem]
    parts = [part for part in re.split(r"[^a-z0-9]+", stem) if part]
    if not parts:
        return f"t{short_hash(track)}"
    abbreviation = "".join(part[0] + "".join(ch for ch in part[1:] if ch.isdigit()) for part in parts)
    abbreviation = safe_fragment(abbreviation.lower())[:18]
    return f"{abbreviation}{short_hash(track, 3)}"


def promptkit(tool_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "promptkit.render", *args],
        cwd=tool_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"promptkit failed ({' '.join(args)}): {completed.stdout.strip()}")
    return completed.stdout


def render_track_prompt(
    *,
    tool_root: Path,
    runner_dir: Path,
    shared_prompt_source: Path,
    track_prompt_source: Path,
    prompt_vars_path: Path,
) -> Path:
    shared_lint = runner_dir / "prompt.shared.lint.txt"
    track_lint = runner_dir / "prompt.track.lint.txt"
    rendered_shared = runner_dir / "prompt.shared.md"
    rendered_track = runner_dir / "prompt.track.md"
    final_prompt = runner_dir / "prompt.md"

    shared_lint.write_text(
        promptkit(tool_root, ["lint", str(shared_prompt_source), "--vars", str(prompt_vars_path)]),
        encoding="utf-8",
    )
    track_lint.write_text(
        promptkit(tool_root, ["lint", str(track_prompt_source), "--vars", str(prompt_vars_path)]),
        encoding="utf-8",
    )
    promptkit(
        tool_root,
        ["render", str(shared_prompt_source), "--vars", str(prompt_vars_path), "--out", str(rendered_shared)],
    )
    promptkit(
        tool_root,
        ["render", str(track_prompt_source), "--vars", str(prompt_vars_path), "--out", str(rendered_track)],
    )
    prompt = rendered_shared.read_text(encoding="utf-8") + "\n\n---\n\n" + rendered_track.read_text(encoding="utf-8")
    final_prompt.write_text(prompt, encoding="utf-8")
    return final_prompt


def render_single_prompt(
    *,
    tool_root: Path,
    runner_dir: Path,
    prompt_source: Path,
    prompt_vars_path: Path,
) -> Path:
    lint_path = runner_dir / "prompt.lint.txt"
    rendered_path = runner_dir / "prompt.rendered.md"
    lint_path.write_text(
        promptkit(tool_root, ["lint", str(prompt_source), "--vars", str(prompt_vars_path)]),
        encoding="utf-8",
    )
    promptkit(tool_root, ["render", str(prompt_source), "--vars", str(prompt_vars_path), "--out", str(rendered_path)])
    return rendered_path


def mint_token(
    *,
    source_root: Path,
    env_id: str = DEFAULT_ENVIRONMENT,
    task_id: str,
    track: str | None = None,
    tick_budget: int,
    soft_stop_tick: int | None,
    goal_json: str,
    soft_stop_scoring: str | None = "binary",
    max_new_games: int = 1,
    token_role: str = "official",
    official: bool = True,
    scoring: str | None = "single",
    data_path: str | None = None,
    ttl_seconds: int = 14400,
    crit_mode: str | None = "random",
    crit_charge_bonus: float | None = None,
    crit_random_chance: float | None = None,
    crit_random_bonus: float | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "server.py",
    ]
    if env_id != DEFAULT_ENVIRONMENT:
        command.extend(["--env", env_id])
    command.extend([
        "mint-token",
        "--task-id",
        task_id,
        "--max-new-games",
        str(max_new_games),
        "--ttl-seconds",
        str(ttl_seconds),
        "--tick-budget",
        str(tick_budget),
        "--goal-json",
        goal_json,
        "--token-role",
        token_role,
    ])
    if soft_stop_tick is not None:
        command.extend(["--soft-stop-tick", str(soft_stop_tick)])
        if soft_stop_scoring:
            command.extend(["--soft-stop-scoring", soft_stop_scoring])
    if track:
        command.extend(["--track", track])
    if scoring:
        command.extend(["--scoring", scoring])
    if data_path:
        command.extend(["--data-path", data_path])
    command.append("--official" if official else "--unofficial")
    if crit_mode is not None:
        command.extend(["--crit-mode", crit_mode])
    if crit_charge_bonus is not None:
        command.extend(["--crit-charge-bonus", str(crit_charge_bonus)])
    if crit_random_chance is not None:
        command.extend(["--crit-random-chance", str(crit_random_chance)])
    if crit_random_bonus is not None:
        command.extend(["--crit-random-bonus", str(crit_random_bonus)])
    completed = subprocess.run(
        command,
        cwd=source_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"mint-token failed: {completed.stdout.strip()}")
    return json.loads(completed.stdout)


def _load_track(
    *,
    source_root: Path,
    track_config_path: str,
    track: str,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    config_path = resolve_source_path(source_root, track_config_path)
    config = load_json(config_path)
    tracks = config["tracks"]
    if track not in tracks:
        known = ", ".join(sorted(tracks))
        raise ValueError(f"unknown track {track!r}; known tracks: {known}")
    return config, tracks[track], config_path


def _tracks_for_suite(config: dict[str, Any], suite: str) -> list[str]:
    tracks = config.get("tracks", {})
    suites = config.get("suites", {})
    if suite == "full" and suite not in suites:
        return list(tracks.keys())
    suite_config = suites.get(suite)
    if suite_config is None:
        known = ", ".join(sorted([*suites.keys(), "full"]))
        raise ValueError(f"unknown suite {suite!r}; known suites: {known}")
    if isinstance(suite_config, list):
        return [str(item) for item in suite_config]
    if isinstance(suite_config, dict):
        return [str(item) for item in suite_config.get("tracks", [])]
    raise ValueError(f"suite {suite!r} must be a list or object with a tracks list")


def resolve_track_selection(
    config: dict[str, Any],
    *,
    requested_tracks: list[str] | None = None,
    requested_suites: list[str] | None = None,
) -> list[str]:
    tracks = config.get("tracks", {})
    selected: list[str] = []

    def add(track: str) -> None:
        if track not in tracks:
            known = ", ".join(sorted(tracks))
            raise ValueError(f"unknown track {track!r}; known tracks: {known}")
        if track not in selected:
            selected.append(track)

    suites = list(requested_suites or [])
    direct_tracks = list(requested_tracks or [])
    if not suites and not direct_tracks:
        default_suite = config.get("default_suite")
        if default_suite:
            suites.append(str(default_suite))
        else:
            direct_tracks = list(tracks.keys())

    for suite in suites:
        for track in _tracks_for_suite(config, suite):
            add(track)
    for track in direct_tracks:
        add(track)
    return selected


def _configured_practice_mode(track_config: dict[str, Any]) -> str:
    practice = track_config.get("practice")
    if isinstance(practice, dict) and practice.get("mode"):
        return str(practice["mode"])
    return "whitebox" if bool(track_config.get("offline_practice", True)) else "none"


def _resolve_practice_mode(track_config: dict[str, Any], offline_practice: bool | None) -> tuple[str, bool]:
    configured_mode = _configured_practice_mode(track_config)
    if offline_practice is None:
        return configured_mode, configured_mode == "whitebox"
    if offline_practice:
        return "whitebox", True
    if configured_mode == "whitebox":
        return "none", False
    return configured_mode, False


def _official_attempts(track_config: dict[str, Any]) -> int:
    official = track_config.get("official")
    if isinstance(official, dict) and official.get("max_new_games") is not None:
        return max(1, int(official["max_new_games"]))
    if track_config.get("official_attempts") is not None:
        return max(1, int(track_config["official_attempts"]))
    return 1


def _official_scoring(track_config: dict[str, Any], attempts: int) -> str:
    official = track_config.get("official")
    if isinstance(official, dict) and official.get("scoring"):
        return str(official["scoring"])
    if track_config.get("official_scoring"):
        return str(track_config["official_scoring"])
    return "best_of_n" if attempts > 1 else "single"


def _resolve_soft_stop(
    config: dict[str, Any],
    hard_budget: int,
    *,
    default_gap: int | None = 20,
) -> tuple[int | None, int | None]:
    if config.get("soft_stop") is False:
        return None, None
    if "soft_stop_tick" in config:
        configured_tick = config.get("soft_stop_tick")
        if configured_tick is None:
            return None, None
        tick = int(configured_tick)
        return tick, max(0, int(hard_budget) - tick)
    configured_gap = config.get("soft_stop_gap", default_gap)
    if configured_gap is None:
        return None, None
    gap = int(configured_gap)
    return max(0, int(hard_budget) - gap), gap


def _soft_stop_profile(soft_stop_tick: int | None, soft_stop_scoring: str | None) -> str:
    if soft_stop_tick is None:
        return "disabled; only the hard budget is enforced and route quality comes from the environment score"
    return (
        f"soft stop at {soft_stop_tick}; scoring policy {soft_stop_scoring or 'binary'}; "
        "advisory only and never a hard cutoff"
    )


def _soft_stop_guidance(soft_stop_tick: int | None) -> str:
    if soft_stop_tick is None:
        return "Soft stop is disabled for this track; judge route quality by final score and hard-budget legality."
    return (
        f"Treat move {soft_stop_tick} as a soft scoring line, not the hard cutoff. "
        "Before crossing it, checkpoint carefully and avoid speculative movement. "
        "At or after it, only spend additional hard-budget moves when you can name "
        "a short command sequence that completes a known official goal."
    )


def _resolve_track_data_path(
    *,
    source_root: Path,
    environment_root: Path,
    config: dict[str, Any],
    track_config: dict[str, Any],
) -> Path | None:
    raw_path = str(track_config.get("data_path") or config.get("default_data_path") or "").strip()
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    normalized = raw_path.replace("\\", "/")
    environment_candidate = (environment_root / candidate).resolve()
    if environment_candidate.exists() or normalized.startswith("data/"):
        return environment_candidate
    return (source_root / candidate).resolve()


def _track_data_context(
    *,
    source_root: Path,
    environment_root: Path,
    config: dict[str, Any],
    track_config: dict[str, Any],
) -> dict[str, Any]:
    data_path = _resolve_track_data_path(
        source_root=source_root,
        environment_root=environment_root,
        config=config,
        track_config=track_config,
    )
    if data_path is None or not data_path.exists():
        return {
            "data_file": str(data_path) if data_path else None,
            "floor_count": None,
            "final_floor": "",
            "final_boss": "",
        }
    data = load_json(data_path)
    floors = sorted(data.get("floors", []), key=lambda item: int(item.get("index", 0)))
    floor_ids = [str(floor["id"]) for floor in floors]
    final_floor = floor_ids[-1] if floor_ids else ""
    return {
        "data_file": str(data_path),
        "floor_count": len(floor_ids),
        "final_floor": final_floor,
        "final_boss": f"{final_floor}_boss" if final_floor else "",
    }


def _resolve_goal_number(value: Any, data_context: dict[str, Any]) -> int:
    if isinstance(value, dict):
        floor_count = int(data_context.get("floor_count") or 0)
        by_floor = value.get("by_floor_count")
        if isinstance(by_floor, dict):
            keyed = by_floor.get(str(floor_count))
            if keyed is not None:
                return int(keyed)
        if "default" in value and "base" not in value and "per_floor" not in value:
            return int(value["default"])
        base = int(value.get("base", value.get("default", 0)))
        per_floor = int(value.get("per_floor", 0))
        return base + per_floor * floor_count
    return int(value)


def _resolve_track_goal(goal: dict[str, Any], data_context: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in goal.items():
        if key == "floor" and str(value) in {"$final_floor", "final", "final_floor"}:
            resolved[key] = data_context.get("final_floor") or value
        elif key == "boss" and str(value) in {"$final_boss", "final", "final_boss"}:
            resolved[key] = data_context.get("final_boss") or value
        elif key.endswith("_min") or key in {"moves_max", "tick_budget", "lifetime_tick_budget"}:
            resolved[key] = _resolve_goal_number(value, data_context)
        else:
            resolved[key] = value
    return resolved


def prepare_track_run(
    *,
    source_root: Path,
    runner: str,
    runner_client: str,
    model: str,
    reasoning_variant: str,
    track: str,
    track_config_path: str,
    shared_prompt_path: str = "",
    prompt_path: str = "",
    out_dir: str,
    tick_budget: int | None,
    server_url: str,
    label_prefix: str,
    report_name_template: str,
    offline_practice: bool | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    tool_root = source_root.parent
    config, track_config, config_path = _load_track(
        source_root=source_root,
        track_config_path=track_config_path,
        track=track,
    )
    environment_root = environment_root_for_config(source_root, config_path)
    env_id = str(config.get("env_id") or (environment_root.name if environment_root.parent.name == "envs" else DEFAULT_ENVIRONMENT))
    sdk_config = dict(config.get("sdk") or {})
    direct_sdk_class = str(sdk_config.get("direct_class") or "ArcaneLabSDK")
    server_sdk_class = str(sdk_config.get("server_class") or "ArcaneLabServerSDK")
    server_url_env = str(sdk_config.get("server_url_env") or "ARCANE_LAB_SERVER_URL")
    auth_token_env = str(sdk_config.get("auth_token_env") or "ARCANE_LAB_AUTH_TOKEN")
    data_path_env = str(sdk_config.get("data_path_env") or "")
    practice_auth_token_env = str(
        sdk_config.get("practice_auth_token_env")
        or auth_token_env.replace("_AUTH_TOKEN", "_PRACTICE_AUTH_TOKEN")
    )
    orchestration = track_config.get("orchestration")
    if track_config.get("orchestration_only") or orchestration:
        orchestration_type = "unknown"
        if isinstance(orchestration, dict):
            orchestration_type = str(orchestration.get("type", orchestration_type))
        raise ValueError(
            f"track {track!r} is orchestration-only ({orchestration_type}) and cannot be run by "
            "the normal single-session runner. Use a warmup/fork orchestrator that creates the "
            "warmup base session and independent forked solve attempts."
        )
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_model = safe_fragment(model.replace("/", "_").replace("\\", "_").replace(":", "_"))
    safe_track = safe_fragment(track)
    label = f"{label_prefix}-{safe_model}-{safe_track}"
    run_root = (source_root / out_dir).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    run_dir = ensure_unique_dir(run_root / f"{label}_{timestamp}")
    runner_dir = run_dir / ".runner"
    logs_dir = run_dir / "logs"
    runner_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    helper_timeout_seconds = DEFAULT_HELPER_TIMEOUT_SECONDS
    python_helper_guard_path = write_python_helper_guard(runner_dir, helper_timeout_seconds)

    practice_mode, resolved_offline_practice = _resolve_practice_mode(track_config, offline_practice)
    data_path = str(track_config.get("data_path") or "")
    practice_config = dict(track_config.get("practice") or {})
    official_attempts = _official_attempts(track_config)
    official_scoring_policy = _official_scoring(track_config, official_attempts)
    workspace_manifest_path = runner_dir / "workspace_manifest.json"
    workspace_manifest = setup_workspace(
        source_root=environment_root,
        dest_root=run_dir,
        profile="track",
        track=track,
        manifest_out=workspace_manifest_path,
        offline_practice=resolved_offline_practice,
        environment=env_id,
    )
    codex_hook_config = write_codex_tool_hook_config(source_root, runner_dir)
    workspace_data_path = ""
    if data_path:
        workspace_data_path = str((run_dir / Path(data_path.replace("\\", "/"))).resolve())

    shared_prompt_rel = shared_prompt_path or track_config.get("shared_prompt_path") or config["default_shared_prompt_path"]
    prompt_rel = prompt_path or track_config["prompt_path"]
    shared_prompt_source = resolve_source_path(environment_root, shared_prompt_rel)
    track_prompt_source = resolve_source_path(environment_root, prompt_rel)

    default_tick_budget = int(track_config["tick_budget"])
    resolved_tick_budget = int(tick_budget) if tick_budget is not None else default_tick_budget
    tick_budget_source = "explicit" if tick_budget is not None else "track-default"
    soft_stop_tick, soft_stop_gap = _resolve_soft_stop(track_config, resolved_tick_budget, default_gap=20)
    soft_stop_scoring = str(track_config.get("soft_stop_scoring", "binary")) if soft_stop_tick is not None else None
    soft_stop_profile = _soft_stop_profile(soft_stop_tick, soft_stop_scoring)
    soft_stop_guidance = _soft_stop_guidance(soft_stop_tick)
    data_context = _track_data_context(
        source_root=source_root,
        environment_root=environment_root,
        config=config,
        track_config=track_config,
    )
    raw_goal = dict(track_config["goal"])
    resolved_goal = _resolve_track_goal(raw_goal, data_context)
    goal_json = json.dumps(resolved_goal, separators=(",", ":"))
    supports_crit = env_id == DEFAULT_ENVIRONMENT or bool(track_config.get("crit")) or bool(config.get("supports_crit"))
    crit_config = dict(track_config.get("crit") or {})
    crit_mode = str(crit_config.get("mode", "random")) if supports_crit else None
    crit_charge_bonus = crit_config.get("charge_bonus") if supports_crit else None
    crit_random_chance = crit_config.get("random_chance") if supports_crit else None
    crit_random_bonus = crit_config.get("random_bonus") if supports_crit else None
    if supports_crit:
        base_random_chance = float(crit_random_chance if crit_random_chance is not None else 0.18)
        base_random_bonus = float(crit_random_bonus if crit_random_bonus is not None else 0.2)
        base_charge_bonus = float(crit_charge_bonus if crit_charge_bonus is not None else 0.2)
        crit_rules = (
            f"Official crit rules: mode `{crit_mode}`; base random chance {base_random_chance * 100:.0f}%; "
            f"random crit attack bonus +{base_random_bonus * 100:.0f}%; charge crit attack bonus "
            f"+{base_charge_bonus * 100:.0f}%."
        )
        practice_kwargs = [f"crit_mode={crit_mode!r}", "crit_seed='practice-seed'"]
        if crit_charge_bonus is not None:
            practice_kwargs.append(f"crit_charge_bonus={float(crit_charge_bonus)!r}")
        if crit_random_chance is not None:
            practice_kwargs.append(f"crit_random_chance={float(crit_random_chance)!r}")
        if crit_random_bonus is not None:
            practice_kwargs.append(f"crit_random_bonus={float(crit_random_bonus)!r}")
        crit_practice_kwargs = ", ".join(practice_kwargs)
    else:
        crit_rules = "This environment has no stochastic crit rules; all combat previews are deterministic."
        crit_practice_kwargs = ""
    rationale = str(track_config.get("budget_rationale", ""))
    budget_profile = (
        f"explicit -TickBudget {resolved_tick_budget} for {track}; track default would be {default_tick_budget}, "
        f"{soft_stop_profile}; {rationale}"
        if tick_budget_source == "explicit"
        else f"track default for {track}: hard {resolved_tick_budget}, {soft_stop_profile}; {rationale}"
    )
    reference_policy = "\n".join(str(line) for line in track_config.get("reference_policy", []))
    helper_profile = track_config.get("helper_profile")
    provided_helper_paths = list(track_config.get("provided_helper_paths", []))
    practice_max_new_games = int(practice_config.get("max_new_games", 0) or 0)
    practice_tick_budget = int(practice_config.get("tick_budget", resolved_tick_budget))
    practice_soft_stop_tick, practice_soft_stop_gap = _resolve_soft_stop(
        practice_config,
        practice_tick_budget,
        default_gap=soft_stop_gap,
    )
    practice_soft_stop_scoring = (
        str(practice_config.get("soft_stop_scoring", soft_stop_scoring or "binary"))
        if practice_soft_stop_tick is not None
        else None
    )
    if practice_mode == "whitebox":
        offline_practice_policy = (
            f"The workspace includes whitebox offline practice support. Use `{direct_sdk_class}` for direct local "
            f"games, then spend official server attempts carefully with `{server_sdk_class}`."
        )
    elif practice_mode == "server-token":
        if practice_max_new_games < 1:
            raise ValueError(f"track {track!r} practice mode server-token requires practice.max_new_games >= 1")
        offline_practice_policy = (
            f"This track provides a separate non-official server practice token. Use "
            f"`{server_sdk_class}(new=True, label=\"{label}-practice\", token_role=\"practice\")` for up to "
            f"{practice_max_new_games} practice game(s), with practice move budget {practice_tick_budget}. "
            "Practice games cannot be verified and never count as official score. Use the default "
            f"`{server_sdk_class}` constructor for official attempts."
        )
    else:
        offline_practice_policy = (
            f"This track provides no practice token and no direct local engine. Do not attempt `{direct_sdk_class}` "
            f"direct local games; use only `{server_sdk_class}` against official server attempts."
        )
    official_attempt_policy = (
        f"The official server token permits {official_attempts} new official server game"
        f"{'' if official_attempts == 1 else 's'}. "
    )
    if official_attempts > 1 or official_scoring_policy == "best_of_n":
        official_attempt_policy += (
            "If you verify multiple official games for this task, the runner score is the best verified official "
            "attempt by verification reward; ties are resolved by accepted outcome and route quality. "
            "Calling verify() submits and closes that official game, so each later scored sample must use a fresh "
            "official game with new=True. Official attempt count is based on official game creation, not active "
            "open games; verify() never refunds, frees, or restores an official attempt."
        )
    else:
        official_attempt_policy += "This is a single official scored attempt. Calling verify() submits and closes it."
    report_name = report_name_template.format(track=track, safe_model=safe_model, timestamp=timestamp)
    report_path = f"logs\\{report_name}"
    task_id = f"{label}-{timestamp}"

    prompt_vars = {
        "WORKSPACE": str(run_dir),
        "RUNNER_CLIENT": runner_client,
        "MODEL": model,
        "REASONING_VARIANT": reasoning_variant,
        "TICK_BUDGET": resolved_tick_budget,
        "LABEL": label,
        "TRACK": track,
        "SAFE_MODEL": safe_model,
        "TIMESTAMP": timestamp,
        "SOFT_STOP_TICK": str(soft_stop_tick) if soft_stop_tick is not None else "disabled",
        "SOFT_STOP_PROFILE": soft_stop_profile,
        "SOFT_STOP_GUIDANCE": soft_stop_guidance,
        "BUDGET_PROFILE": budget_profile,
        "REPORT_PATH": report_path,
        "REFERENCE_POLICY": reference_policy,
        "OFFLINE_PRACTICE_POLICY": offline_practice_policy,
        "PRACTICE_MODE": practice_mode,
        "PRACTICE_AUTH_TOKEN_ENV": practice_auth_token_env,
        "PRACTICE_MAX_NEW_GAMES": practice_max_new_games,
        "PRACTICE_TICK_BUDGET": practice_tick_budget,
        "OFFICIAL_ATTEMPTS": official_attempts,
        "OFFICIAL_SCORING_POLICY": official_scoring_policy,
        "OFFICIAL_ATTEMPT_POLICY": official_attempt_policy,
        "CRIT_RULES": crit_rules,
        "CRIT_PRACTICE_KWARGS": crit_practice_kwargs,
        "ENV_ID": env_id,
        "DIRECT_SDK_CLASS": direct_sdk_class,
        "SERVER_SDK_CLASS": server_sdk_class,
        "SERVER_URL_ENV": server_url_env,
        "AUTH_TOKEN_ENV": auth_token_env,
        "HELPER_TIMEOUT_SECONDS": helper_timeout_seconds,
        "FLOOR_COUNT": data_context.get("floor_count") or "",
        "FINAL_FLOOR": data_context.get("final_floor") or "",
        "FINAL_BOSS": data_context.get("final_boss") or "",
        "ROUTE_SCORE_MIN": resolved_goal.get("route_score_min", ""),
        "GOAL_JSON": goal_json,
    }
    prompt_vars_path = runner_dir / "prompt.vars.json"
    prompt_vars_path.write_text(json.dumps(prompt_vars, indent=2, ensure_ascii=False), encoding="utf-8")
    rendered_prompt_path = render_track_prompt(
        tool_root=tool_root,
        runner_dir=runner_dir,
        shared_prompt_source=shared_prompt_source,
        track_prompt_source=track_prompt_source,
        prompt_vars_path=prompt_vars_path,
    )

    practice_token = None
    practice_task_id = None
    if practice_mode == "server-token":
        practice_task_id = f"{task_id}-practice"
        practice_token = mint_token(
            source_root=source_root,
            env_id=env_id,
            task_id=practice_task_id,
            track=track,
            tick_budget=practice_tick_budget,
            soft_stop_tick=practice_soft_stop_tick,
            soft_stop_scoring=practice_soft_stop_scoring,
            goal_json=goal_json,
            max_new_games=practice_max_new_games,
            token_role="practice",
            official=False,
            scoring="practice_not_scored",
            crit_mode=crit_mode,
            crit_charge_bonus=crit_charge_bonus,
            crit_random_chance=crit_random_chance,
            crit_random_bonus=crit_random_bonus,
            data_path=data_path or None,
        )

    token = mint_token(
        source_root=source_root,
        env_id=env_id,
        task_id=task_id,
        track=track,
        tick_budget=resolved_tick_budget,
        soft_stop_tick=soft_stop_tick,
        soft_stop_scoring=soft_stop_scoring,
        goal_json=goal_json,
        max_new_games=official_attempts,
        token_role="official",
        official=True,
        scoring=official_scoring_policy,
        crit_mode=crit_mode,
        crit_charge_bonus=crit_charge_bonus,
        crit_random_chance=crit_random_chance,
        crit_random_bonus=crit_random_bonus,
        data_path=data_path or None,
    )

    metadata = {
        "runner": runner,
        "model": model,
        "reasoning_variant": reasoning_variant,
        "track": track,
        "workspace": str(run_dir),
        "runner_dir": str(runner_dir),
        "track_config": str(config_path),
        "env_id": env_id,
        "environment_root": str(environment_root),
        "workspace_setup": str(workspace_manifest_path),
        "workspace_setup_profile": workspace_manifest["profile"],
        "offline_practice": resolved_offline_practice,
        "practice_mode": practice_mode,
        "workspace_mode": workspace_manifest["workspace_mode"],
        "workspace_setup_items": [
            item["item"] for item in workspace_manifest["items"] if item.get("status") == "copied"
        ],
        "prompt_renderer": "promptkit",
        "promptkit_root": str(tool_root),
        "prompt_vars": str(prompt_vars_path),
        "prompt_template": str(rendered_prompt_path),
        "shared_prompt_template": str(shared_prompt_source),
        "track_prompt_template": str(track_prompt_source),
        "shared_prompt_rendered": str(runner_dir / "prompt.shared.md"),
        "track_prompt_rendered": str(runner_dir / "prompt.track.md"),
        "shared_prompt_lint": str(runner_dir / "prompt.shared.lint.txt"),
        "track_prompt_lint": str(runner_dir / "prompt.track.lint.txt"),
        "timestamp": timestamp,
        "server_url": server_url,
        "token_task_id": task_id,
        "official_attempts": official_attempts,
        "official_scoring_policy": official_scoring_policy,
        "token_tick_budget": resolved_tick_budget,
        "token_tick_budget_source": tick_budget_source,
        "token_track_default_tick_budget": default_tick_budget,
        "token_tick_budget_type": "lifetime",
        "token_lifetime_tick_budget": resolved_tick_budget,
        "token_soft_stop_tick": soft_stop_tick,
        "token_soft_stop_gap": soft_stop_gap,
        "token_soft_stop_scoring": soft_stop_scoring,
        "token_crit_mode": crit_mode,
        "token_crit_charge_bonus": crit_charge_bonus,
        "token_crit_random_chance": crit_random_chance,
        "token_crit_random_bonus": crit_random_bonus,
        "budget_profile": budget_profile,
        "source_policy_extra_forbidden": track_config.get("source_policy_extra_forbidden", []),
        "token_goal_json": goal_json,
        "raw_goal_json": json.dumps(raw_goal, separators=(",", ":")),
        "resolved_goal_json": goal_json,
        "floor_count": data_context.get("floor_count"),
        "final_floor": data_context.get("final_floor") or None,
        "final_boss": data_context.get("final_boss") or None,
        "track_data_file": data_context.get("data_file"),
        "crit_mode": crit_mode,
        "crit_rules": crit_rules,
        "direct_sdk_class": direct_sdk_class,
        "server_sdk_class": server_sdk_class,
        "server_url_env": server_url_env,
        "auth_token_env": auth_token_env,
        "data_path": data_path or None,
        "data_path_env": data_path_env or None,
        "workspace_data_path": workspace_data_path or None,
        "practice_auth_token_env": practice_auth_token_env,
        "practice_token_task_id": practice_task_id,
        "practice_max_new_games": practice_max_new_games if practice_mode == "server-token" else None,
        "practice_tick_budget": practice_tick_budget if practice_mode == "server-token" else None,
        "practice_soft_stop_tick": practice_soft_stop_tick if practice_mode == "server-token" else None,
        "practice_soft_stop_gap": practice_soft_stop_gap if practice_mode == "server-token" else None,
        "practice_soft_stop_scoring": practice_soft_stop_scoring if practice_mode == "server-token" else None,
        "helper_profile": helper_profile,
        "provided_helper_paths": provided_helper_paths,
        "python_helper_timeout_seconds": helper_timeout_seconds,
        "python_helper_guard_path": str(python_helper_guard_path),
        **codex_hook_config,
    }
    metadata_path = runner_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        **metadata,
        "metadata": str(metadata_path),
        "run_dir": str(run_dir),
        "logs_dir": str(logs_dir),
        "runner_dir": str(runner_dir),
        "label": label,
        "safe_model": safe_model,
        "safe_track": safe_track,
        "timestamp": timestamp,
        "task_id": task_id,
        "tick_budget": resolved_tick_budget,
        "soft_stop_tick": soft_stop_tick,
        "goal_json": goal_json,
        "auth_token": token["token"],
        "practice_auth_token": practice_token["token"] if practice_token else None,
        "prompt": rendered_prompt_path.read_text(encoding="utf-8"),
    }


def prepare_prompt_run(
    *,
    source_root: Path,
    runner: str,
    model: str,
    effort: str,
    prompt_path: str,
    out_dir: str,
    workspace_profile: str,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    tool_root = source_root.parent
    prompt_source = resolve_source_path(source_root, prompt_path)
    environment_root = environment_root_for_config(source_root, prompt_source)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_model = safe_fragment(model)
    label = f"deepseek-{safe_model}"
    run_root = (source_root / out_dir).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    run_dir = ensure_unique_dir(run_root / f"{safe_model}_{timestamp}")
    runner_dir = run_dir / ".runner"
    logs_dir = run_dir / "logs"
    runner_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    workspace_manifest_path = runner_dir / "workspace_manifest.json"
    workspace_manifest = setup_workspace(
        source_root=environment_root,
        dest_root=run_dir,
        profile=workspace_profile,
        track=None,
        manifest_out=workspace_manifest_path,
    )
    prompt_vars = {
        "WORKSPACE": str(run_dir),
        "MODEL": model,
        "EFFORT": effort,
        "SAFE_MODEL": safe_model,
        "TIMESTAMP": timestamp,
        "LABEL": label,
    }
    prompt_vars_path = runner_dir / "prompt.vars.json"
    prompt_vars_path.write_text(json.dumps(prompt_vars, indent=2, ensure_ascii=False), encoding="utf-8")
    rendered_prompt_path = render_single_prompt(
        tool_root=tool_root,
        runner_dir=runner_dir,
        prompt_source=prompt_source,
        prompt_vars_path=prompt_vars_path,
    )
    final_prompt_path = runner_dir / "prompt.md"
    prompt_body = rendered_prompt_path.read_text(encoding="utf-8")
    if str(run_dir) not in prompt_body:
        prompt_body = prompt_body.replace(str(source_root), str(run_dir))
    prompt = (
        f"Runner model: {model}\n"
        f"Runner effort: {effort}\n"
        f"Runner isolated workspace: {run_dir}\n"
        f"Runner output directory: {runner_dir}\n\n"
        f"{prompt_body}"
    )
    final_prompt_path.write_text(prompt, encoding="utf-8")

    metadata = {
        "runner": runner,
        "model": model,
        "effort": effort,
        "workspace": str(run_dir),
        "runner_dir": str(runner_dir),
        "workspace_setup": str(workspace_manifest_path),
        "environment_root": str(environment_root),
        "workspace_setup_profile": workspace_profile,
        "workspace_setup_items": [
            item["item"] for item in workspace_manifest["items"] if item.get("status") == "copied"
        ],
        "prompt_renderer": "promptkit",
        "promptkit_root": str(tool_root),
        "prompt_source": str(prompt_source),
        "prompt_vars": str(prompt_vars_path),
        "prompt_rendered": str(rendered_prompt_path),
        "prompt_lint": str(runner_dir / "prompt.lint.txt"),
        "prompt_final": str(final_prompt_path),
        "timestamp": timestamp,
    }
    metadata_path = runner_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        **metadata,
        "metadata": str(metadata_path),
        "run_dir": str(run_dir),
        "logs_dir": str(logs_dir),
        "runner_dir": str(runner_dir),
        "label": label,
        "safe_model": safe_model,
        "timestamp": timestamp,
        "prompt": prompt,
    }


def load_verifications(source_root: Path, task_id: str) -> list[tuple[dict[str, Any], Path]]:
    games_root = source_root / "logs" / "server" / "games"
    if not games_root.exists():
        return []
    matches: list[tuple[dict[str, Any], Path]] = []
    files = sorted(games_root.rglob("verification.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = load_json(path)
        except Exception:
            continue
        if data.get("task_id") == task_id:
            matches.append((data, path))
    return matches


def _verification_route_score(verification: dict[str, Any]) -> float:
    score = verification.get("score") or {}
    metrics = score.get("metrics") or {}
    for key in ("route_score", "routeScore"):
        value = metrics.get(key, score.get(key))
        if value is not None:
            parsed = _as_float(value)
            return parsed if parsed is not None else 0.0
    return 0.0


def _verification_rank(verification: dict[str, Any], path: Path) -> tuple[Any, ...]:
    completion = verification_goal_completion(verification) or {}
    reward = _as_int(verification.get("reward"))
    soft_stop_score = _as_float(verification.get("softStopScore"))
    tick_used = _as_int(verification.get("tickBudgetUsed"))
    return (
        reward if reward is not None else -1,
        int(bool(verification.get("accepted"))),
        int(verification_outcome(verification) == "success"),
        int(completion.get("achieved_count", 0) or 0),
        _verification_route_score(verification),
        soft_stop_score if soft_stop_score is not None else -1.0,
        -(tick_used if tick_used is not None else 10**12),
        path.stat().st_mtime,
    )


def select_best_verification(
    candidates: list[tuple[dict[str, Any], Path]],
) -> tuple[dict[str, Any] | None, Path | None]:
    if not candidates:
        return None, None
    return max(candidates, key=lambda item: _verification_rank(item[0], item[1]))


def load_verification(source_root: Path, task_id: str) -> tuple[dict[str, Any] | None, Path | None]:
    return select_best_verification(load_verifications(source_root, task_id))


def _goal_status_achieved(status: Any) -> bool:
    if isinstance(status, bool):
        return status
    if isinstance(status, dict) and "achieved" in status:
        return bool(status["achieved"])
    return bool(status)


def verification_goal_completion(verification: dict[str, Any] | None) -> dict[str, Any] | None:
    if not verification:
        return None
    existing = verification.get("goalCompletion")
    if isinstance(existing, dict):
        failed = list(existing.get("failed", []))
        total = int(existing.get("total", 0) or 0)
        achieved_count = int(existing.get("achievedCount", total - len(failed)) or 0)
        return {
            "achieved": existing.get("achieved"),
            "achieved_count": achieved_count,
            "total": total,
            "failed": failed,
        }
    goal_status = (verification.get("score") or {}).get("goal") or {}
    failed = [
        name
        for name, status in goal_status.items()
        if not _goal_status_achieved(status)
    ]
    total = len(goal_status)
    return {
        "achieved": None if total == 0 else not failed,
        "achieved_count": total - len(failed),
        "total": total,
        "failed": failed,
    }


def verification_outcome(verification: dict[str, Any] | None) -> str | None:
    if not verification:
        return None
    if isinstance(verification.get("outcome"), str):
        return verification["outcome"]
    accepted = bool(verification.get("accepted"))
    completion = verification_goal_completion(verification)
    goal_achieved = completion.get("achieved") if completion else None
    if not accepted:
        return "rejected"
    if goal_achieved is False:
        return "partial"
    if goal_achieved is True:
        return "success"
    return "accepted"


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _quality_grade(score: float) -> str:
    if score >= 0.90:
        return "S"
    if score >= 0.80:
        return "A"
    if score >= 0.65:
        return "B"
    if score >= 0.50:
        return "C"
    if score >= 0.35:
        return "D"
    return "F"


def _goal_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    raw = metadata.get("token_goal_json")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _load_trajectory(verification_path: Path | None) -> dict[str, Any] | None:
    if not verification_path:
        return None
    trajectory_path = verification_path.with_name("trajectory.json")
    if not trajectory_path.exists():
        return None
    try:
        return load_json(trajectory_path)
    except Exception:
        return None


def _crit_route_signals(verification: dict[str, Any], verification_path: Path | None) -> dict[str, Any]:
    final = verification.get("final", {}) if verification else {}
    crit = final.get("crit", {}) if isinstance(final, dict) else {}
    trajectory = _load_trajectory(verification_path)
    roll_count = 0
    triggered_count = 0
    if trajectory:
        for entry in trajectory.get("entries", []):
            output = str(entry.get("output", "")).lower()
            roll_count += len(re.findall(r"\b(?:no crit|crit) \(", output))
            triggered_count += len(re.findall(r"(?<!no )\bcrit \(", output))
    trigger_rate = (triggered_count / roll_count) if roll_count else None
    return {
        "mode": crit.get("mode"),
        "random_chance": crit.get("random_chance"),
        "random_bonus": crit.get("random_bonus"),
        "charge_bonus": crit.get("charge_bonus"),
        "combat_roll_count": roll_count,
        "triggered_count": triggered_count,
        "trigger_rate": round(trigger_rate, 4) if trigger_rate is not None else None,
    }


def route_quality(
    *,
    verification: dict[str, Any] | None,
    verification_path: Path | None,
    policy: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if not verification:
        return {
            "score": 0.0,
            "grade": "F",
            "components": {"verification": 0.0},
            "signals": {},
            "warnings": ["no verification.json found for this task"],
        }

    metrics = verification.get("trajectoryMetrics") or {}
    final = verification.get("final") or {}
    goal = _goal_from_metadata(metadata)
    goal_completion = verification_goal_completion(verification)
    warnings: list[str] = []
    components: dict[str, float | None] = {}
    signals: dict[str, Any] = {}

    accepted = bool(verification.get("accepted"))
    goal_achieved = goal_completion.get("achieved") if goal_completion else None
    if not accepted:
        components["goal"] = 0.0
    elif goal_completion and goal_completion.get("total"):
        total = max(1, int(goal_completion.get("total") or 0))
        achieved_count = int(goal_completion.get("achieved_count") or 0)
        components["goal"] = achieved_count / total
    else:
        components["goal"] = 1.0 if goal_achieved is not False else 0.0

    tick_budget = (
        _as_int(verification.get("lifetimeTickBudget"))
        or _as_int(verification.get("tickBudget"))
        or _as_int(metadata.get("token_lifetime_tick_budget"))
        or _as_int(metadata.get("token_tick_budget"))
    )
    lifetime_tick = (
        _as_int(metrics.get("final_lifetime_tick"))
        or _as_int(verification.get("lifetimeTickBudgetUsed"))
        or _as_int(verification.get("tickBudgetUsed"))
        or _as_int(final.get("lifetime_tick"))
        or _as_int(final.get("tick"))
    )
    if tick_budget and lifetime_tick is not None:
        used_ratio = lifetime_tick / tick_budget
        components["tick_efficiency"] = _clamp01(1.0 - used_ratio)
        signals["budget_used_ratio"] = round(used_ratio, 4)
    else:
        components["tick_efficiency"] = None

    soft_score = _as_float(verification.get("softStopScore"))
    components["soft_stop"] = 1.0 if soft_score is None else _clamp01(soft_score)

    failed_commands = _as_int(metrics.get("failed_command_count")) or 0
    command_count = _as_int(metrics.get("command_count")) or max(0, int(verification.get("entryCount", 1) or 1) - 1)
    failure_tolerance = max(3.0, command_count * 0.1)
    components["command_cleanliness"] = _clamp01(1.0 - (failed_commands / failure_tolerance))

    policy_violations = int((policy or {}).get("violation_count", 0) or 0)
    components["source_policy"] = 1.0 if policy_violations == 0 else 0.0
    if policy_violations:
        warnings.append(f"{policy_violations} source-policy violation(s) detected")

    required_retirements = _as_int(goal.get("retirements"))
    retirements = _as_int(final.get("retirements")) or 0
    if required_retirements:
        components["retirement_target"] = _clamp01(retirements / required_retirements)
    else:
        components["retirement_target"] = None

    crit_signals = _crit_route_signals(verification, verification_path)
    if (
        crit_signals.get("mode") == "random"
        and crit_signals.get("triggered_count")
        and accepted
        and goal_achieved is not False
    ):
        warnings.append("random crits occurred; rerun with another seed before treating the route as stable")

    signals.update(
        {
            "accepted": accepted,
            "outcome": verification_outcome(verification),
            "lifetime_tick": lifetime_tick,
            "tick_budget": tick_budget,
            "soft_stop_tick": verification.get("softStopTick") or metadata.get("token_soft_stop_tick"),
            "soft_stop_scoring": verification.get("softStopScoring") or metadata.get("token_soft_stop_scoring"),
            "command_count": command_count,
            "failed_command_count": failed_commands,
            "retirements": retirements,
            "required_retirements": required_retirements,
            "retirement_ticks": metrics.get("retirement_ticks"),
            "post_retire_ticks": metrics.get("post_retire_ticks"),
            "crit": crit_signals,
        }
    )

    weights = {
        "goal": 0.40,
        "tick_efficiency": 0.25,
        "soft_stop": 0.10,
        "command_cleanliness": 0.10,
        "source_policy": 0.10,
        "retirement_target": 0.05,
    }
    weighted_total = 0.0
    weight_used = 0.0
    for name, weight in weights.items():
        component = components.get(name)
        if component is None:
            continue
        weighted_total += component * weight
        weight_used += weight
    score = weighted_total / weight_used if weight_used else 0.0
    rounded_components = {
        name: (round(value, 4) if isinstance(value, float) else value)
        for name, value in components.items()
    }
    return {
        "score": round(score, 4),
        "grade": _quality_grade(score),
        "components": rounded_components,
        "signals": signals,
        "warnings": warnings,
    }


def command_events_from_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for index, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        command = item.get("command")
        if isinstance(command, str):
            events.append({"line": index, "command": command})
    return events


def access_events_from_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    seen_reasonix_tool_payloads: set[tuple[str, str]] = set()

    def add_event(line: int, tool: str, payload: Any) -> None:
        normalized_tool = str(tool or "")
        if normalized_tool.lower() in {"write", "edit", "multiedit", "notebookedit", "todowrite"}:
            return
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        events.append({"line": line, "tool": normalized_tool, "payload": text})

    for index, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue

        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "command_execution":
            command = item.get("command")
            if isinstance(command, str):
                add_event(index, "command_execution", command)

        part = event.get("part")
        if isinstance(part, dict) and event.get("type") == "tool_use":
            state = part.get("state")
            payload = state.get("input") if isinstance(state, dict) else None
            if payload is not None:
                add_event(index, str(part.get("tool") or ""), payload)

        message = event.get("message")
        if isinstance(message, dict):
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    add_event(index, str(block.get("name") or ""), block.get("input") or {})

        stream_event = event.get("event")
        if isinstance(stream_event, dict) and stream_event.get("type") == "content_block_start":
            block = stream_event.get("content_block")
            if isinstance(block, dict) and block.get("type") == "tool_use":
                add_event(index, str(block.get("name") or ""), block.get("input") or {})

        # Reasonix transcripts record tool activity as loop records with
        # role=tool_start/tool and tool/args fields.
        role = str(event.get("role") or "")
        if role in {"tool_start", "tool"}:
            tool = str(event.get("tool") or event.get("toolName") or "tool")
            payload = event.get("args")
            if payload is None:
                payload = event.get("toolArgs")
            if payload is not None:
                normalized_payload = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, sort_keys=True)
                reasonix_key = (tool, normalized_payload)
                if reasonix_key not in seen_reasonix_tool_payloads:
                    seen_reasonix_tool_payloads.add(reasonix_key)
                    add_event(index, tool, payload)

        params = event.get("params")
        if isinstance(params, dict):
            update = params.get("update")
            if isinstance(update, dict) and update.get("sessionUpdate") == "tool_call":
                raw_input = update.get("rawInput")
                if raw_input is not None:
                    add_event(index, str(update.get("title") or "tool_call"), raw_input)

    return events


def source_policy(output_path: Path, extra_patterns: list[dict[str, str]]) -> dict[str, Any]:
    patterns: list[dict[str, str]] = [
        {
            "name": "data-file",
            "pattern": "data\\arcane_lab.json",
            "regex": r"(^|[\\/\"'\s])data[\\/]+arcane_lab\.json([\"'\s]|$)",
        },
        {
            "name": "game-source",
            "pattern": "game.py",
            "regex": r"(^|[\\/\"'\s])game\.py([\"'\s]|$)",
        },
        {
            "name": "server-source",
            "pattern": "server.py",
            "regex": r"(^|[\\/\"'\s])server\.py([\"'\s]|$)",
        },
        {
            "name": "mcp-source",
            "pattern": "mcp_server.py",
            "regex": r"(^|[\\/\"'\s])mcp_server\.py([\"'\s]|$)",
        },
        {
            "name": "sdk-source",
            "pattern": "sdk\\arcane_lab_sdk.py",
            "regex": r"(^|[\\/\"'\s])sdk[\\/]+arcane_lab_sdk\.py([\"'\s]|$)",
        },
        {
            "name": "sdk-server-source",
            "pattern": "sdk\\server_sdk.py",
            "regex": r"(^|[\\/\"'\s])sdk[\\/]+server_sdk\.py([\"'\s]|$)",
        },
        {
            "name": "sdk-init-source",
            "pattern": "sdk\\__init__.py",
            "regex": r"(^|[\\/\"'\s])sdk[\\/]+__init__\.py([\"'\s]|$)",
        },
        {
            "name": "sdk-result-source",
            "pattern": "sdk\\result.py",
            "regex": r"(^|[\\/\"'\s])sdk[\\/]+result\.py([\"'\s]|$)",
        },
        {"name": "sdk-glob", "pattern": "sdk/**/*"},
        {
            "name": "sdk-dir-list",
            "pattern": "sdk directory listing",
            "regex": r"\b(ls|dir|gci|get-childitem|rg|find)\b[^\n\r]*\bsdk\b",
        },
        {
            "name": "data-dir-list",
            "pattern": "data directory listing",
            "regex": r"\b(ls|dir|gci|get-childitem|rg|find)\b[^\n\r]*\bdata\b",
        },
        {
            "name": "script-smoke",
            "pattern": "scripts\\smoke.txt",
            "regex": r"(^|[\\/\"'\s])scripts[\\/]+smoke\.txt([\"'\s]|$)",
        },
        {
            "name": "script-midgame",
            "pattern": "scripts\\midgame_smoke.txt",
            "regex": r"(^|[\\/\"'\s])scripts[\\/]+midgame_smoke\.txt([\"'\s]|$)",
        },
        {
            "name": "script-late",
            "pattern": "scripts\\late_playtest.txt",
            "regex": r"(^|[\\/\"'\s])scripts[\\/]+late_playtest\.txt([\"'\s]|$)",
        },
        {
            "name": "script-retire",
            "pattern": "scripts\\retire_smoke.txt",
            "regex": r"(^|[\\/\"'\s])scripts[\\/]+retire_smoke\.txt([\"'\s]|$)",
        },
        {
            "name": "script-prestige",
            "pattern": "scripts\\prestige_smoke.txt",
            "regex": r"(^|[\\/\"'\s])scripts[\\/]+prestige_smoke\.txt([\"'\s]|$)",
        },
        {"name": "debug-goals", "pattern": "goals_debug"},
        {"name": "debug-goals-cli", "pattern": "list goals debug"},
    ]
    patterns.extend(extra_patterns or [])
    violations = []
    for event in access_events_from_jsonl(output_path):
        payload = event["payload"]
        lowered = payload.lower()
        for pattern in patterns:
            regex = pattern.get("regex")
            if regex:
                if re.search(str(regex), payload, flags=re.IGNORECASE):
                    violations.append(
                        {
                            "line": event["line"],
                            "tool": event.get("tool"),
                            "name": pattern.get("name"),
                            "pattern": pattern.get("pattern"),
                            "access": payload,
                        }
                    )
                continue
            needle = str(pattern.get("pattern", "")).lower()
            if needle and needle in lowered:
                violations.append(
                    {
                        "line": event["line"],
                        "tool": event.get("tool"),
                        "name": pattern.get("name"),
                        "pattern": pattern.get("pattern"),
                        "access": payload,
                    }
                )
    return {"violation_count": len(violations), "violations": violations}


def build_track_summary(
    *,
    source_root: Path,
    metadata_path: Path,
    output_path: Path,
    report_path: Path | None,
    stopped_reason: str | None,
    exit_code: int | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = load_json(metadata_path)
    task_id = str(metadata.get("token_task_id") or "")
    verification_candidates = load_verifications(source_root, task_id)
    verification, verification_path = select_best_verification(verification_candidates)
    final = verification.get("final", {}) if verification else {}
    final_state = final.get("state", {}) if isinstance(final.get("state"), dict) else {}
    goal_completion = verification_goal_completion(verification)
    policy = source_policy(output_path, metadata.get("source_policy_extra_forbidden", []))
    quality = route_quality(
        verification=verification,
        verification_path=verification_path,
        policy=policy,
        metadata=metadata,
    )
    summary: dict[str, Any] = {
        "runner": metadata.get("runner"),
        "model": metadata.get("model"),
        "reasoning_variant": metadata.get("reasoning_variant") or metadata.get("effort"),
        "track": metadata.get("track"),
        "run_dir": metadata.get("workspace"),
        "output": str(output_path),
        "report": str(report_path) if report_path else None,
        "stopped_reason": stopped_reason,
        "exit_code": exit_code,
        "task_id": task_id or None,
        "verification_path": str(verification_path) if verification_path else None,
        "verification_candidate_count": len(verification_candidates),
        "verification_selection_policy": metadata.get("official_scoring_policy") or "single",
        "game_id": verification.get("game_id") if verification else None,
        "reward": verification.get("reward") if verification else None,
        "accepted": verification.get("accepted") if verification else None,
        "outcome": verification_outcome(verification),
        "goal_achieved": goal_completion.get("achieved") if goal_completion else None,
        "goal_completion": goal_completion,
        "goal_failed": goal_completion.get("failed") if goal_completion else None,
        "tick": final.get("tick"),
        "lifetime_tick": final.get("lifetime_tick"),
        "moves": final.get("moves"),
        "floor": final.get("floor"),
        "hp": final_state.get("hp"),
        "atk": final_state.get("atk"),
        "def": final_state.get("def"),
        "gold": final_state.get("gold"),
        "victory": final_state.get("victory"),
        "soft_stop_tick": verification.get("softStopTick") if verification else metadata.get("token_soft_stop_tick"),
        "soft_stop_exceeded": verification.get("softStopExceeded") if verification else None,
        "soft_stop_score": verification.get("softStopScore") if verification else None,
        "compliance_score": verification.get("complianceScore") if verification else None,
        "source_policy": policy,
        "route_quality": quality,
        "run": final.get("run"),
        "retirements": final.get("retirements"),
        "insight": final.get("insight"),
        "trajectory_hash": verification.get("trajectory_hash") if verification else None,
    }
    if extra:
        summary.update(extra)
    atif_path = None
    try:
        from atif_export import build_atif_trajectory, write_json as write_atif_json

        runner_dir = Path(metadata.get("runner_dir") or metadata_path.parent)
        atif_path = runner_dir / "atif_trajectory.json"
        trajectory = _load_trajectory(verification_path)
        atif_payload = build_atif_trajectory(
            metadata=metadata,
            summary=summary,
            trajectory=trajectory,
            verification=verification,
            trajectory_path=verification_path.with_name("trajectory.json") if verification_path else None,
            verification_path=verification_path,
            output_path=output_path,
            report_path=report_path,
            extra=summary,
        )
        write_atif_json(atif_path, atif_payload)
        summary["atif_trajectory"] = str(atif_path)
    except Exception as exc:
        summary["atif_export_error"] = repr(exc)
    return summary
