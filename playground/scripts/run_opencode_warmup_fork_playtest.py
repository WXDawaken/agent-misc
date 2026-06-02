from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import runner_common as common
from setup_agent_workspace import setup_workspace


DEFAULT_WARMUP_ARTIFACTS = [
    "mechanics.md",
    "gotchas.md",
    "warmup_summary.md",
]
HANDOFF_MODES = ("session-fork", "artifact-only", "cold-solve")
HANDOFF_MODE_CODES = {
    "session-fork": "sf",
    "artifact-only": "ao",
    "cold-solve": "cold",
}


def uses_artifact_handoff(handoff_mode: str) -> bool:
    return handoff_mode in {"session-fork", "artifact-only"}


def uses_session_fork(handoff_mode: str) -> bool:
    return handoff_mode == "session-fork"


def handoff_context_policy(handoff_mode: str) -> str:
    if handoff_mode == "session-fork":
        return (
            "You are continuing from a fork of the warmup session. Use both the inherited "
            "warmup context and the copied warmup artifacts, but do not inspect sibling solve attempts."
        )
    if handoff_mode == "artifact-only":
        return (
            "You are a fresh solve session. Use only the copied warmup artifacts and files in this "
            "workspace as warmup memory; do not assume hidden transcript context from the base session."
        )
    if handoff_mode == "cold-solve":
        return (
            "You are a fresh solve session with no warmup artifact handoff. Treat this as a cold "
            "solve control and rely on the allowed docs plus offline practice."
        )
    raise ValueError(f"unknown handoff mode: {handoff_mode}")


def warmup_artifact_names(track_config: dict[str, Any]) -> list[str]:
    configured = track_config.get("warmup_artifacts") or DEFAULT_WARMUP_ARTIFACTS
    names: list[str] = []
    for item in configured:
        normalized = str(item).replace("\\", "/").strip("/")
        if normalized:
            names.append(normalized.split("/")[-1])
    return names or list(DEFAULT_WARMUP_ARTIFACTS)


def resolve_opencode_command(opencode_bin: str) -> list[str]:
    candidate = Path(opencode_bin)
    if candidate.exists():
        if candidate.suffix.lower() in {".cmd", ".bat"}:
            direct = resolve_opencode_node_entry(candidate)
            if direct:
                return direct
            return [shutil.which("cmd.exe") or "cmd.exe", "/c", str(candidate)]
        return [str(candidate)]
    for name in (f"{opencode_bin}.cmd", f"{opencode_bin}.exe", opencode_bin):
        resolved = shutil.which(name)
        if resolved:
            if Path(resolved).suffix.lower() in {".cmd", ".bat"}:
                direct = resolve_opencode_node_entry(Path(resolved))
                if direct:
                    return direct
                return [shutil.which("cmd.exe") or "cmd.exe", "/c", resolved]
            return [resolved]
    return [opencode_bin]


def resolve_opencode_node_entry(wrapper: Path) -> list[str] | None:
    wrapper_dir = wrapper.parent
    node_script = wrapper_dir / "node_modules" / "opencode-ai" / "bin" / "opencode"
    if not node_script.exists():
        return None
    bundled_node = wrapper_dir / "node.exe"
    if bundled_node.exists():
        return [str(bundled_node), str(node_script)]
    node = shutil.which("node.exe") or shutil.which("node")
    if node:
        return [node, str(node_script)]
    return None


def stop_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.kill()


def run_opencode(
    *,
    opencode_bin: str,
    workspace: Path,
    runner_dir: Path,
    model: str,
    reasoning_variant: str,
    title: str,
    message: str,
    timeout_minutes: int,
    env_overrides: dict[str, str | None],
    session_id: str | None = None,
    fork: bool = False,
    report_pattern: str | None = None,
    stop_after_report_seconds: int = 45,
    warmup_artifacts: list[Path] | None = None,
    stop_after_artifacts_seconds: int = 60,
) -> dict[str, Any]:
    runner_dir.mkdir(parents=True, exist_ok=True)
    out_path = runner_dir / "opencode_output.jsonl"
    raw_path = runner_dir / "opencode_stdout.log"
    err_path = runner_dir / "opencode_error.log"

    command = resolve_opencode_command(opencode_bin) + [
        "run",
        "--dir",
        str(workspace),
        "-m",
        model,
        "--variant",
        reasoning_variant,
        "--agent",
        "build",
        "--format",
        "json",
        "--title",
        title,
    ]
    if session_id:
        command.extend(["--session", session_id])
    if fork:
        command.append("--fork")
    command.extend(["--", message])

    env = os.environ.copy()
    for key in list(env):
        if key.startswith("ARCANE_LAB_"):
            env.pop(key, None)
    for key, value in env_overrides.items():
        if value is not None:
            env[key] = str(value)

    started = time.time()
    process = subprocess.Popen(
        command,
        cwd=workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None

    sentinel = object()
    line_queue: queue.Queue[str | object] = queue.Queue()

    def read_stdout() -> None:
        assert process.stdout is not None
        try:
            for stdout_line in process.stdout:
                line_queue.put(stdout_line)
        finally:
            line_queue.put(sentinel)

    threading.Thread(target=read_stdout, daemon=True).start()

    latest_report: Path | None = None
    report_first_seen_at: float | None = None
    artifact_first_seen_at: float | None = None
    stopped_reason: str | None = None
    event_count = 0
    session_seen: str | None = None
    usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0}

    with raw_path.open("w", encoding="utf-8") as raw_handle, out_path.open("w", encoding="utf-8") as jsonl_handle:
        stdout_done = False

        def record_line(line: str) -> None:
            nonlocal event_count, session_seen
            raw_handle.write(line)
            raw_handle.flush()
            stripped = line.strip()
            if not stripped.startswith("{"):
                return
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                return
            jsonl_handle.write(json.dumps(event, ensure_ascii=True) + "\n")
            jsonl_handle.flush()
            event_count += 1
            session_seen = session_seen or event.get("sessionID") or (event.get("part") or {}).get("sessionID")
            tokens = ((event.get("part") or {}).get("tokens") or {}) if isinstance(event.get("part"), dict) else {}
            if tokens:
                usage["input_tokens"] += int(tokens.get("input") or 0)
                usage["output_tokens"] += int(tokens.get("output") or 0)
                usage["reasoning_tokens"] += int(tokens.get("reasoning") or 0)
                cache = tokens.get("cache") or {}
                usage["cache_read_tokens"] += int(cache.get("read") or 0)
                usage["cache_write_tokens"] += int(cache.get("write") or 0)

        while True:
            try:
                queued = line_queue.get(timeout=1)
            except queue.Empty:
                queued = None

            if queued is sentinel:
                stdout_done = True
            elif isinstance(queued, str):
                record_line(queued)

            if report_pattern:
                reports = sorted((workspace / "logs").glob(report_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
                if reports:
                    if latest_report is None or reports[0] != latest_report:
                        latest_report = reports[0]
                        report_first_seen_at = time.time()
                    elif (
                        stop_after_report_seconds > 0
                        and report_first_seen_at is not None
                        and time.time() - report_first_seen_at >= stop_after_report_seconds
                        and process.poll() is None
                    ):
                        stopped_reason = "stopped_after_report"
                        stop_process_tree(process)

            if warmup_artifacts:
                if all(path.exists() and path.stat().st_size > 0 for path in warmup_artifacts):
                    if artifact_first_seen_at is None:
                        artifact_first_seen_at = time.time()
                    elif (
                        stop_after_artifacts_seconds > 0
                        and time.time() - artifact_first_seen_at >= stop_after_artifacts_seconds
                        and process.poll() is None
                    ):
                        stopped_reason = "stopped_after_warmup_artifacts"
                        stop_process_tree(process)
                else:
                    artifact_first_seen_at = None

            if stdout_done and process.poll() is not None:
                break

            if time.time() - started >= timeout_minutes * 60:
                stopped_reason = "timeout"
                stop_process_tree(process)
                break

        while True:
            try:
                queued = line_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(queued, str):
                record_line(queued)

    try:
        exit_code = process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        stop_process_tree(process)
        exit_code = 124
    if stopped_reason == "timeout":
        exit_code = 124
    err_path.write_text("", encoding="utf-8")

    return {
        "command": command[:-1] + ["<message>"],
        "output": str(out_path),
        "raw_output": str(raw_path),
        "error_log": str(err_path),
        "report": str(latest_report) if latest_report else None,
        "stopped_reason": stopped_reason,
        "exit_code": exit_code,
        "session_id": session_seen,
        "event_count": event_count,
        "usage": usage,
        "wall_clock_sec": round(time.time() - started, 3),
    }


def render_prompt(
    *,
    source_root: Path,
    runner_dir: Path,
    prompt_path: str,
    prompt_vars: dict[str, Any],
    shared_prompt_path: str | None = None,
) -> Path:
    vars_path = runner_dir / "prompt.vars.json"
    vars_path.write_text(json.dumps(prompt_vars, indent=2, ensure_ascii=False), encoding="utf-8")
    if shared_prompt_path:
        return common.render_track_prompt(
            tool_root=source_root.parent,
            runner_dir=runner_dir,
            shared_prompt_source=common.resolve_source_path(source_root, shared_prompt_path),
            track_prompt_source=common.resolve_source_path(source_root, prompt_path),
            prompt_vars_path=vars_path,
        )
    return common.render_single_prompt(
        tool_root=source_root.parent,
        runner_dir=runner_dir,
        prompt_source=common.resolve_source_path(source_root, prompt_path),
        prompt_vars_path=vars_path,
    )


def crit_prompt_fields(track_config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    crit_config = dict(track_config.get("crit") or {})
    mode = str(crit_config.get("mode", "random"))
    charge_bonus = crit_config.get("charge_bonus")
    random_chance = crit_config.get("random_chance")
    random_bonus = crit_config.get("random_bonus")
    base_random_chance = float(random_chance if random_chance is not None else 0.18)
    base_random_bonus = float(random_bonus if random_bonus is not None else 0.2)
    base_charge_bonus = float(charge_bonus if charge_bonus is not None else 0.2)
    crit_rules = (
        f"Official crit rules: mode `{mode}`; base random chance {base_random_chance * 100:.0f}%; "
        f"random crit attack bonus +{base_random_bonus * 100:.0f}%; charge crit attack bonus "
        f"+{base_charge_bonus * 100:.0f}%."
    )
    practice_kwargs = [f"crit_mode={mode!r}", "crit_seed='practice-seed'"]
    if charge_bonus is not None:
        practice_kwargs.append(f"crit_charge_bonus={float(charge_bonus)!r}")
    if random_chance is not None:
        practice_kwargs.append(f"crit_random_chance={float(random_chance)!r}")
    if random_bonus is not None:
        practice_kwargs.append(f"crit_random_bonus={float(random_bonus)!r}")
    return crit_rules, ", ".join(practice_kwargs), crit_config


def make_solve_vars(
    *,
    run_dir: Path,
    runner_client: str,
    model: str,
    reasoning_variant: str,
    track: str,
    label: str,
    safe_model: str,
    timestamp: str,
    tick_budget: int,
    soft_stop_tick: int,
    soft_stop_gap: int,
    budget_rationale: str,
    report_path: str,
    reference_policy: str,
    offline_practice: bool,
    crit_rules: str,
    crit_practice_kwargs: str,
    handoff_mode: str,
    handoff_policy: str,
) -> dict[str, Any]:
    offline_policy = (
        "The workspace includes offline practice support. Use `ArcaneLabSDK` for direct local games "
        "for offline practice, then spend the official server game carefully with `ArcaneLabServerSDK`."
        if offline_practice
        else "This track does not provide offline practice. Do not attempt `ArcaneLabSDK` direct local games; "
        "use only `ArcaneLabServerSDK` against the official server game."
    )
    return {
        "WORKSPACE": str(run_dir),
        "RUNNER_CLIENT": runner_client,
        "MODEL": model,
        "REASONING_VARIANT": reasoning_variant,
        "TICK_BUDGET": tick_budget,
        "LABEL": label,
        "TRACK": track,
        "SAFE_MODEL": safe_model,
        "TIMESTAMP": timestamp,
        "SOFT_STOP_TICK": soft_stop_tick,
        "BUDGET_PROFILE": f"track default for {track}: hard {tick_budget}, soft stop gap {soft_stop_gap}; {budget_rationale}",
        "REPORT_PATH": report_path,
        "REFERENCE_POLICY": reference_policy,
        "OFFLINE_PRACTICE_POLICY": offline_policy,
        "CRIT_RULES": crit_rules,
        "CRIT_PRACTICE_KWARGS": crit_practice_kwargs,
        "HANDOFF_MODE": handoff_mode,
        "HANDOFF_CONTEXT_POLICY": handoff_policy,
    }


def copy_warmup_artifacts(base_dir: Path, fork_dir: Path, artifact_names: list[str]) -> list[str]:
    copied: list[str] = []
    (fork_dir / "logs").mkdir(parents=True, exist_ok=True)
    for name in artifact_names:
        src = base_dir / "logs" / name
        dst = fork_dir / "logs" / name
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(f"logs\\{name}")
    return copied


def find_report(logs_dir: Path, pattern: str) -> Path | None:
    reports = sorted(logs_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenCode warmup/fork Arcane Lab studies.")
    parser.add_argument("--model", default="opencode-go/deepseek-v4-pro")
    parser.add_argument("--reasoning-variant", default="high")
    parser.add_argument("--track", default="warmup-fork-prestige")
    parser.add_argument("--track-config-path", default="envs/arcane_lab/docs/tracks/config.json")
    parser.add_argument("--out-dir", default="agent_workspaces/w")
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    parser.add_argument("--opencode-bin", default="opencode")
    parser.add_argument("--base-timeout-minutes", type=int, default=90)
    parser.add_argument("--fork-timeout-minutes", type=int, default=90)
    parser.add_argument("--stop-after-artifacts-seconds", type=int, default=60)
    parser.add_argument("--stop-after-report-seconds", type=int, default=45)
    parser.add_argument("--max-bases", type=int)
    parser.add_argument("--forks-per-base", type=int)
    parser.add_argument(
        "--handoff-mode",
        choices=HANDOFF_MODES,
        default="session-fork",
        help=(
            "How solve attempts receive warmup context: session-fork keeps the current OpenCode "
            "--session --fork behavior plus copied artifacts; artifact-only starts a fresh session "
            "with copied artifacts; cold-solve starts a fresh session without copied artifacts."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = Path.cwd().resolve()
    config_path = common.resolve_source_path(source_root, args.track_config_path)
    environment_root = common.environment_root_for_config(source_root, config_path)
    config = common.load_json(config_path)
    track_config = config["tracks"].get(args.track)
    if not track_config:
        known = ", ".join(sorted(config["tracks"]))
        raise SystemExit(f"unknown track {args.track!r}; known tracks: {known}")
    orchestration = track_config.get("orchestration") or {}
    if orchestration.get("type") != "warmup_fork":
        raise SystemExit(f"track {args.track!r} is not a warmup_fork orchestration track")

    phase_paths = track_config["phase_prompt_paths"]
    warmup_workspace_track = str(track_config.get("warmup_workspace_track") or args.track)
    base_count = int(args.max_bases or orchestration.get("base_count", 1))
    forks_per_base = int(args.forks_per_base or orchestration.get("forks_per_base", 1))
    tick_budget = int(track_config["tick_budget"])
    soft_stop_gap = int(track_config.get("soft_stop_gap", 20))
    soft_stop_tick = max(0, tick_budget - soft_stop_gap)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_stamp = common.short_timestamp()
    safe_model = common.safe_fragment(args.model.replace("/", "_").replace("\\", "_").replace(":", "_"))
    safe_track = common.safe_fragment(args.track)
    short_model = common.short_model_id(args.model)
    short_track = common.short_track_id(args.track)
    short_handoff = HANDOFF_MODE_CODES[args.handoff_mode]
    run_id_base = f"ocw-{short_model}-{short_track}-{short_handoff}-{run_stamp}"
    study_root = common.ensure_unique_dir((source_root / args.out_dir / run_id_base).resolve())
    run_id = study_root.name
    study_root.mkdir(parents=True, exist_ok=True)
    matrix_path = study_root / "warmup_matrix.json"

    crit_rules, crit_practice_kwargs, crit_config = crit_prompt_fields(track_config)
    configured_warmup_artifacts = warmup_artifact_names(track_config)
    reference_policy = "\n".join(str(line) for line in track_config.get("reference_policy", []))
    goal_json = json.dumps(track_config["goal"], separators=(",", ":"))
    shared_prompt_path = config["default_shared_prompt_path"]

    print(f"STUDY_ROOT={study_root}")
    print(
        f"TRACK={args.track} MODEL={args.model} VARIANT={args.reasoning_variant} "
        f"HANDOFF_MODE={args.handoff_mode} BASES={base_count} FORKS_PER_BASE={forks_per_base}"
    )

    all_results: dict[str, Any] = {
        "runner": "opencode-warmup-fork",
        "model": args.model,
        "reasoning_variant": args.reasoning_variant,
        "track": args.track,
        "handoff_mode": args.handoff_mode,
        "artifact_handoff": uses_artifact_handoff(args.handoff_mode),
        "session_fork": uses_session_fork(args.handoff_mode),
        "run_id": run_id,
        "short_model": short_model,
        "short_track": short_track,
        "short_handoff": short_handoff,
        "warmup_artifacts": [f"logs\\{name}" for name in configured_warmup_artifacts],
        "warmup_workspace_track": warmup_workspace_track,
        "study_root": str(study_root),
        "base_count": base_count,
        "forks_per_base": forks_per_base,
        "bases": [],
    }

    for base_index in range(1, base_count + 1):
        base_label = f"{run_id}-b{base_index}"
        base_dir = study_root / f"b{base_index}"
        base_runner_dir = base_dir / ".runner"
        setup_workspace(
            source_root=environment_root,
            dest_root=base_dir,
            profile="track",
            track=warmup_workspace_track,
            manifest_out=base_runner_dir / "workspace_manifest.json",
            offline_practice=bool(track_config.get("offline_practice", True)),
        )
        base_prompt_path = render_prompt(
            source_root=source_root,
            runner_dir=base_runner_dir,
            prompt_path=phase_paths["warmup"],
            prompt_vars={"TRACK": args.track},
        )
        base_prompt = (
            "The complete warmup prompt is included below. Do not search for a prompt file; "
            "use this message as the authoritative warmup task. This phase must not create "
            "an official server game.\n\n"
            + base_prompt_path.read_text(encoding="utf-8")
        )
        base_metadata = {
            "runner": "opencode-warmup-fork",
            "phase": "warmup",
            "model": args.model,
            "reasoning_variant": args.reasoning_variant,
            "track": args.track,
            "workspace_setup_track": warmup_workspace_track,
            "handoff_mode": args.handoff_mode,
            "workspace": str(base_dir),
            "runner_dir": str(base_runner_dir),
            "prompt_template": str(base_prompt_path),
            "timestamp": timestamp,
            "run_id": run_id,
            "short_model": short_model,
            "short_track": short_track,
            "base_index": base_index,
            "official_new_games_allowed": 0,
            "warmup_artifacts": [f"logs\\{name}" for name in configured_warmup_artifacts],
            "source_policy_extra_forbidden": track_config.get(
                "warmup_source_policy_extra_forbidden",
                track_config.get("source_policy_extra_forbidden", []),
            ),
        }
        (base_runner_dir / "metadata.json").write_text(json.dumps(base_metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"BASE {base_index}: RUN_DIR={base_dir}")
        base_run = run_opencode(
            opencode_bin=args.opencode_bin,
            workspace=base_dir,
            runner_dir=base_runner_dir,
            model=args.model,
            reasoning_variant=args.reasoning_variant,
            title=f"arcane-lab-{base_label}",
            message=base_prompt,
            timeout_minutes=args.base_timeout_minutes,
            env_overrides={},
            warmup_artifacts=[base_dir / "logs" / name for name in configured_warmup_artifacts],
            stop_after_artifacts_seconds=args.stop_after_artifacts_seconds,
        )
        base_summary = common.build_track_summary(
            source_root=source_root,
            metadata_path=base_runner_dir / "metadata.json",
            output_path=Path(base_run["output"]),
            report_path=None,
            stopped_reason=base_run["stopped_reason"],
            exit_code=base_run["exit_code"],
            extra={
                "phase": "warmup",
                "run_id": run_id,
                "short_model": short_model,
                "short_track": short_track,
                "short_handoff": short_handoff,
                "handoff_mode": args.handoff_mode,
                "base_index": base_index,
                "session_id": base_run.get("session_id"),
                "raw_output": base_run["raw_output"],
                "event_count": base_run["event_count"],
                "usage": base_run["usage"],
                "wall_clock_sec": base_run["wall_clock_sec"],
                "warmup_artifacts": {
                    f"logs\\{name}": (base_dir / "logs" / name).exists()
                    for name in configured_warmup_artifacts
                },
            },
        )
        (base_runner_dir / "summary.json").write_text(json.dumps(base_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        base_entry: dict[str, Any] = {"base": base_summary, "forks": []}
        all_results["bases"].append(base_entry)
        matrix_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        artifacts_ready = all(
            (base_dir / "logs" / name).exists() and (base_dir / "logs" / name).stat().st_size > 0
            for name in configured_warmup_artifacts
        )
        if uses_artifact_handoff(args.handoff_mode) and not artifacts_ready:
            print(f"BASE {base_index}: warmup artifacts are incomplete; skipping forks")
            continue
        if uses_session_fork(args.handoff_mode) and not base_run.get("session_id"):
            print(f"BASE {base_index}: no OpenCode session id found; skipping forks")
            continue

        for fork_index in range(1, forks_per_base + 1):
            fork_label = f"{run_id}-b{base_index}f{fork_index}"
            fork_dir = study_root / f"b{base_index}_f{fork_index}"
            fork_runner_dir = fork_dir / ".runner"
            setup_workspace(
                source_root=environment_root,
                dest_root=fork_dir,
                profile="track",
                track=args.track,
                manifest_out=fork_runner_dir / "workspace_manifest.json",
                offline_practice=bool(track_config.get("offline_practice", True)),
            )
            copied_artifacts = (
                copy_warmup_artifacts(base_dir, fork_dir, configured_warmup_artifacts)
                if uses_artifact_handoff(args.handoff_mode)
                else []
            )
            fork_timestamp = common.short_timestamp()
            task_id = fork_label
            report_name = f"{fork_label}_report.md"
            report_path = f"logs\\{report_name}"
            token = common.mint_token(
                source_root=source_root,
                task_id=task_id,
                tick_budget=tick_budget,
                soft_stop_tick=soft_stop_tick,
                goal_json=goal_json,
                crit_mode=str(crit_config.get("mode", "random")),
                crit_charge_bonus=crit_config.get("charge_bonus"),
                crit_random_chance=crit_config.get("random_chance"),
                crit_random_bonus=crit_config.get("random_bonus"),
            )
            solve_vars = make_solve_vars(
                run_dir=fork_dir,
                runner_client="OpenCode Go Warmup Fork",
                model=args.model,
                reasoning_variant=args.reasoning_variant,
                track=args.track,
                label=fork_label,
                safe_model=safe_model,
                timestamp=fork_timestamp,
                tick_budget=tick_budget,
                soft_stop_tick=soft_stop_tick,
                soft_stop_gap=soft_stop_gap,
                budget_rationale=str(track_config.get("budget_rationale", "")),
                report_path=report_path,
                reference_policy=reference_policy,
                offline_practice=bool(track_config.get("offline_practice", True)),
                crit_rules=crit_rules,
                crit_practice_kwargs=crit_practice_kwargs,
                handoff_mode=args.handoff_mode,
                handoff_policy=handoff_context_policy(args.handoff_mode),
            )
            solve_prompt_path = render_prompt(
                source_root=source_root,
                runner_dir=fork_runner_dir,
                prompt_path=phase_paths["solve"],
                prompt_vars=solve_vars,
                shared_prompt_path=shared_prompt_path,
            )
            solve_prompt = (
                "The complete warmup solve prompt is included below. Do not search for a prompt file; "
                "use the instructions in this message as the authoritative task. "
                f"Handoff mode: {args.handoff_mode}. {handoff_context_policy(args.handoff_mode)} "
                "Do not inspect, print, manually set, or store runner "
                "auth environment variables; the SDK reads them automatically.\n\n"
                + solve_prompt_path.read_text(encoding="utf-8")
            )
            fork_metadata = {
                "runner": "opencode-warmup-fork",
                "phase": "solve",
                "model": args.model,
                "reasoning_variant": args.reasoning_variant,
                "track": args.track,
                "handoff_mode": args.handoff_mode,
                "artifact_handoff": uses_artifact_handoff(args.handoff_mode),
                "session_fork": uses_session_fork(args.handoff_mode),
                "workspace": str(fork_dir),
                "runner_dir": str(fork_runner_dir),
                "track_config": str(config_path),
                "environment_root": str(environment_root),
                "workspace_setup": str(fork_runner_dir / "workspace_manifest.json"),
                "workspace_setup_profile": "track",
                "offline_practice": bool(track_config.get("offline_practice", True)),
                "workspace_mode": "direct-sdk",
                "prompt_renderer": "promptkit",
                "prompt_template": str(solve_prompt_path),
                "shared_prompt_template": str(common.resolve_source_path(source_root, shared_prompt_path)),
                "track_prompt_template": str(common.resolve_source_path(source_root, phase_paths["solve"])),
                "timestamp": fork_timestamp,
                "run_id": run_id,
                "short_model": short_model,
                "short_track": short_track,
                "short_handoff": short_handoff,
                "server_url": args.server_url,
                "token_task_id": task_id,
                "token_tick_budget": tick_budget,
                "token_tick_budget_source": "track-default",
                "token_track_default_tick_budget": tick_budget,
                "token_tick_budget_type": "lifetime",
                "token_lifetime_tick_budget": tick_budget,
                "token_soft_stop_tick": soft_stop_tick,
                "token_soft_stop_gap": soft_stop_gap,
                "token_crit_mode": str(crit_config.get("mode", "random")),
                "token_crit_charge_bonus": crit_config.get("charge_bonus"),
                "token_crit_random_chance": crit_config.get("random_chance"),
                "token_crit_random_bonus": crit_config.get("random_bonus"),
                "budget_profile": solve_vars["BUDGET_PROFILE"],
                "source_policy_extra_forbidden": track_config.get("source_policy_extra_forbidden", []),
                "token_goal_json": goal_json,
                "helper_profile": track_config.get("helper_profile"),
                "provided_helper_paths": track_config.get("provided_helper_paths", []),
                "base_index": base_index,
                "fork_index": fork_index,
                "solve_index": fork_index,
                "base_session_id": base_run.get("session_id"),
                "used_base_session_id": base_run.get("session_id") if uses_session_fork(args.handoff_mode) else None,
                "copied_warmup_artifacts": copied_artifacts,
            }
            (fork_runner_dir / "metadata.json").write_text(json.dumps(fork_metadata, indent=2, ensure_ascii=False), encoding="utf-8")

            print(f"FORK {base_index}.{fork_index}: RUN_DIR={fork_dir}")
            fork_run = run_opencode(
                opencode_bin=args.opencode_bin,
                workspace=fork_dir,
                runner_dir=fork_runner_dir,
                model=args.model,
                reasoning_variant=args.reasoning_variant,
                title=f"arcane-lab-{fork_label}",
                message=solve_prompt,
                timeout_minutes=args.fork_timeout_minutes,
                env_overrides={
                    "ARCANE_LAB_SERVER_URL": args.server_url,
                    "ARCANE_LAB_AUTH_TOKEN": token["token"],
                    "ARCANE_LAB_CRIT_MODE": str(crit_config.get("mode", "random")),
                    "ARCANE_LAB_CRIT_CHARGE_BONUS": crit_config.get("charge_bonus"),
                    "ARCANE_LAB_CRIT_RANDOM_CHANCE": crit_config.get("random_chance"),
                    "ARCANE_LAB_CRIT_RANDOM_BONUS": crit_config.get("random_bonus"),
                },
                session_id=str(base_run["session_id"]) if uses_session_fork(args.handoff_mode) else None,
                fork=uses_session_fork(args.handoff_mode),
                report_pattern="*_report.md",
                stop_after_report_seconds=args.stop_after_report_seconds,
            )
            report = find_report(fork_dir / "logs", "*_report.md")
            fork_summary = common.build_track_summary(
                source_root=source_root,
                metadata_path=fork_runner_dir / "metadata.json",
                output_path=Path(fork_run["output"]),
                report_path=report,
                stopped_reason=fork_run["stopped_reason"],
                exit_code=fork_run["exit_code"],
                extra={
                    "phase": "solve",
                    "run_id": run_id,
                    "short_model": short_model,
                    "short_track": short_track,
                    "short_handoff": short_handoff,
                    "handoff_mode": args.handoff_mode,
                    "base_index": base_index,
                    "fork_index": fork_index,
                    "solve_index": fork_index,
                    "base_session_id": base_run.get("session_id"),
                    "used_base_session_id": base_run.get("session_id") if uses_session_fork(args.handoff_mode) else None,
                    "session_id": fork_run.get("session_id"),
                    "raw_output": fork_run["raw_output"],
                    "event_count": fork_run["event_count"],
                    "usage": fork_run["usage"],
                    "wall_clock_sec": fork_run["wall_clock_sec"],
                    "copied_warmup_artifacts": copied_artifacts,
                },
            )
            (fork_runner_dir / "summary.json").write_text(json.dumps(fork_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            base_entry["forks"].append(fork_summary)
            matrix_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(fork_summary, indent=2, ensure_ascii=False))

    matrix_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WARMUP_MATRIX={matrix_path}")
    print(json.dumps(all_results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
