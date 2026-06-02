from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import runner_common as common


def resolve_opencode_command(opencode_bin: str) -> list[str]:
    candidate = Path(opencode_bin)
    if candidate.exists():
        direct = resolve_opencode_node_entry(candidate)
        if direct:
            return direct
        return [str(candidate)]

    for name in (f"{opencode_bin}.cmd", f"{opencode_bin}.exe", opencode_bin):
        resolved = shutil.which(name)
        if not resolved:
            continue
        direct = resolve_opencode_node_entry(Path(resolved))
        if direct:
            return direct
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


def latest_report(log_dir: Path, pattern: str) -> Path | None:
    reports = sorted(log_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


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
    prompt_file: Path | None,
    timeout_minutes: int,
    stop_after_report_seconds: int,
    report_pattern: str,
    env_overrides: dict[str, str],
    dangerously_skip_permissions: bool,
) -> dict[str, Any]:
    out_path = runner_dir / "opencode_output.jsonl"
    raw_path = runner_dir / "opencode_stdout.log"
    err_path = runner_dir / "opencode_error.log"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

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
    if prompt_file is not None:
        command.extend(["-f", str(prompt_file)])
    if dangerously_skip_permissions:
        command.append("--dangerously-skip-permissions")
    command.extend(["--", message])

    env = os.environ.copy()
    for key in list(env):
        if key.startswith("ARCANE_LAB_") or key.startswith("LEDGER_TOWER_"):
            env.pop(key, None)
    env.update(env_overrides)

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

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()

    latest = None
    report_first_seen_at = None
    stopped_reason = None
    event_count = 0

    with raw_path.open("w", encoding="utf-8") as raw_handle, out_path.open("w", encoding="utf-8") as jsonl_handle:
        stdout_done = False

        def record_line(line: str) -> None:
            nonlocal event_count
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

        while True:
            try:
                queued = line_queue.get(timeout=1)
            except queue.Empty:
                queued = None

            if queued is sentinel:
                stdout_done = True
            elif isinstance(queued, str):
                record_line(queued)

            report = latest_report(logs_dir, report_pattern)
            if report:
                if latest is None or report != latest:
                    latest = report
                    report_first_seen_at = time.time()
                elif (
                    stop_after_report_seconds > 0
                    and report_first_seen_at is not None
                    and time.time() - report_first_seen_at >= stop_after_report_seconds
                    and process.poll() is None
                ):
                    stopped_reason = "stopped_after_report"
                    stop_process_tree(process)

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
        return_code = process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        stop_process_tree(process)
        return_code = 124
    if stopped_reason == "timeout":
        return_code = 124

    return {
        "command": command[:-1] + ["<message>"],
        "output": str(out_path),
        "raw_output": str(raw_path),
        "error_log": str(err_path),
        "report": str(latest) if latest else None,
        "stopped_reason": stopped_reason,
        "exit_code": return_code,
        "event_count": event_count,
        "wall_clock_sec": round(time.time() - started, 3),
    }


def run_track(args: argparse.Namespace, track: str) -> dict[str, Any]:
    source_root = Path.cwd().resolve()
    label_prefix = "opencode"
    report_template = "opencode_random_playtest_{track}_{safe_model}_{timestamp}_report.md"
    report_pattern = "opencode_random_playtest_*_report.md"
    prepared = common.prepare_track_run(
        source_root=source_root,
        runner="opencode",
        runner_client="OpenCode",
        model=args.model,
        reasoning_variant=args.reasoning_variant,
        track=track,
        track_config_path=args.track_config_path,
        shared_prompt_path=args.shared_prompt_path,
        prompt_path=args.prompt_path,
        out_dir=args.out_dir,
        tick_budget=args.tick_budget,
        server_url=args.server_url,
        label_prefix=label_prefix,
        report_name_template=report_template,
    )

    run_dir = Path(prepared["run_dir"])
    runner_dir = Path(prepared["runner_dir"])
    metadata_path = Path(prepared["metadata"])
    metadata = common.load_json(metadata_path)
    metadata.update(
        {
            "timeout_minutes": args.timeout_minutes,
            "prompt_delivery": "file_attachment",
            "dangerously_skip_permissions": bool(args.dangerously_skip_permissions),
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt_input_path = runner_dir / "opencode_prompt_input.md"
    prompt_input_path.write_text(str(prepared["prompt"]), encoding="utf-8")
    metadata["prompt_input"] = str(prompt_input_path)
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt = (
        "Read the attached playtest prompt file and follow it exactly. "
        "Do not search for another prompt file. "
        "Do not inspect, print, manually set, or store runner auth environment variables; "
        "the SDK reads them automatically. Finish by writing the required report."
    )

    server_url_env = str(prepared.get("server_url_env") or "ARCANE_LAB_SERVER_URL")
    auth_token_env = str(prepared.get("auth_token_env") or "ARCANE_LAB_AUTH_TOKEN")
    env_overrides = {
        server_url_env: str(prepared["server_url"]),
        auth_token_env: str(prepared["auth_token"]),
    }
    practice_auth_token_env = str(prepared.get("practice_auth_token_env") or "")
    if prepared.get("practice_auth_token") and practice_auth_token_env:
        env_overrides[practice_auth_token_env] = str(prepared["practice_auth_token"])
    data_path_env = str(prepared.get("data_path_env") or "")
    if prepared.get("workspace_data_path") and data_path_env:
        env_overrides[data_path_env] = str(prepared["workspace_data_path"])
    if prepared.get("env_id", "arcane_lab") == "arcane_lab":
        env_overrides["ARCANE_LAB_CRIT_MODE"] = str(
            prepared.get("token_crit_mode") or prepared.get("crit_mode") or "random"
        )
        crit_env_names = {
            "token_crit_charge_bonus": "ARCANE_LAB_CRIT_CHARGE_BONUS",
            "token_crit_random_chance": "ARCANE_LAB_CRIT_RANDOM_CHANCE",
            "token_crit_random_bonus": "ARCANE_LAB_CRIT_RANDOM_BONUS",
        }
        for key, env_name in crit_env_names.items():
            if prepared.get(key) is not None:
                env_overrides[env_name] = str(prepared[key])

    title = f"ledger-tower-{prepared['label']}" if prepared.get("env_id") == "ledger_tower" else f"arcane-lab-{prepared['label']}"
    soft_stop_display = "disabled" if prepared.get("soft_stop_tick") is None else str(prepared["soft_stop_tick"])
    print(f"RUN_DIR={run_dir}")
    print(
        f"TRACK={track} MODEL={args.model} VARIANT={args.reasoning_variant} "
        f"BUDGET={prepared['tick_budget']} SOFT_STOP={soft_stop_display}"
    )

    opencode_result = run_opencode(
        opencode_bin=args.opencode_bin,
        workspace=run_dir,
        runner_dir=runner_dir,
        model=args.model,
        reasoning_variant=args.reasoning_variant,
        title=title,
        message=prompt,
        prompt_file=prompt_input_path,
        timeout_minutes=args.timeout_minutes,
        stop_after_report_seconds=args.stop_after_report_seconds,
        report_pattern=report_pattern,
        env_overrides=env_overrides,
        dangerously_skip_permissions=args.dangerously_skip_permissions,
    )

    summary = common.build_track_summary(
        source_root=source_root,
        metadata_path=metadata_path,
        output_path=Path(opencode_result["output"]),
        report_path=Path(opencode_result["report"]) if opencode_result["report"] else None,
        stopped_reason=opencode_result["stopped_reason"],
        exit_code=opencode_result["exit_code"],
        extra={
            "reasoning_variant": args.reasoning_variant,
            "raw_output": opencode_result["raw_output"],
            "event_count": opencode_result["event_count"],
            "wall_clock_sec": opencode_result["wall_clock_sec"],
        },
    )
    (runner_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run game tracks through direct OpenCode providers.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-variant", default="high")
    parser.add_argument("--track-config-path", default="envs/arcane_lab/docs/tracks/config.json")
    parser.add_argument("--track", action="append", help="Track to run. Repeatable. Overrides the default suite when used.")
    parser.add_argument("--suite", action="append", help="Configured suite to run. Defaults to config default_suite.")
    parser.add_argument("--list-tracks", action="store_true")
    parser.add_argument("--shared-prompt-path", default="")
    parser.add_argument("--prompt-path", default="")
    parser.add_argument("--out-dir", default="agent_workspaces/opencode_runs")
    parser.add_argument("--tick-budget", type=int)
    parser.add_argument("--timeout-minutes", type=int, default=60)
    parser.add_argument("--stop-after-report-seconds", type=int, default=45)
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    parser.add_argument("--opencode-bin", default="opencode")
    parser.add_argument("--dangerously-skip-permissions", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = Path.cwd().resolve()
    config = common.load_json(common.resolve_source_path(source_root, args.track_config_path))
    if args.list_tracks:
        print(
            json.dumps(
                {
                    "default_suite": config.get("default_suite"),
                    "suites": config.get("suites", {}),
                    "tracks": list(config.get("tracks", {}).keys()),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    selected = common.resolve_track_selection(config, requested_tracks=args.track, requested_suites=args.suite)
    summaries = [run_track(args, track) for track in selected]
    result_root = source_root / args.out_dir
    result_root.mkdir(parents=True, exist_ok=True)
    matrix_path = result_root / f"opencode_matrix_{time.strftime('%Y%m%d_%H%M%S')}.json"
    matrix_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MATRIX_SUMMARY={matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
