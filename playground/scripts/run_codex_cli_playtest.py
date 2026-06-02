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


OPENCODE_LIKE_PROFILE = """Harness behavior profile: OpenCode-like single-agent run.

This profile is a behavioral shim only. It does not change game rules, reveal
hidden mechanics, alter the reference policy, or grant extra files.

- Work as a single build-style agent inside the provided workspace.
- Treat the inline prompt as the authoritative task source.
- Keep exploration as route research, not broad source or workspace inspection.
- Prefer small bounded Python helpers under `logs\\` that replay candidate
  route files and print compact checkpoint summaries.
- Maintain a compact route file early; iterate by editing route files and
  replaying them rather than building large adaptive autoplay loops.
- Keep helper stdout concise: checkpoint, state delta, failure reason, and next
  repair target are more useful than full trace dumps.
- After the first complete offline success, do at most one named repair or
  compression pass unless a concrete route-breaking bug remains.
- Before official play, make `logs\\final_route.md` the route source of truth.
- During official play, execute the route from `logs\\final_route.md`; diagnose
  divergence with zero-tick observations first, then use only short named
  recovery sequences that still fit the hard budget.
- Verify once the official goal is complete or no legal budget-safe route
  remains, then write the required report promptly.
"""


def harness_profile_prompt(name: str) -> str:
    if name == "codex-default":
        return ""
    if name == "opencode-like":
        return OPENCODE_LIKE_PROFILE.strip()
    raise ValueError(f"unknown harness profile: {name}")


def resolve_codex_command(codex_bin: str) -> list[str]:
    candidate = Path(codex_bin)
    if candidate.exists():
        suffix = candidate.suffix.lower()
        if suffix in {".cmd", ".bat"}:
            return [shutil.which("cmd.exe") or "cmd.exe", "/c", str(candidate)]
        return [str(candidate)]

    for name in (f"{codex_bin}.cmd", f"{codex_bin}.exe", codex_bin):
        resolved = shutil.which(name)
        if not resolved:
            continue
        suffix = Path(resolved).suffix.lower()
        if suffix in {".cmd", ".bat"}:
            return [shutil.which("cmd.exe") or "cmd.exe", "/c", resolved]
        return [resolved]
    return [codex_bin]

def latest_report(log_dir: Path, pattern: str) -> Path | None:
    reports = sorted(log_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def _windows_process_table() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId,ParentProcessId,Name,CommandLine,WorkingSetSize | "
            "ConvertTo-Json -Compress"
        ),
    ]
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    data = json.loads(completed.stdout)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _descendant_pids(root_pid: int, processes: list[dict[str, Any]]) -> set[int]:
    children_by_parent: dict[int, list[int]] = {}
    for proc in processes:
        try:
            pid = int(proc.get("ProcessId"))
            parent = int(proc.get("ParentProcessId"))
        except (TypeError, ValueError):
            continue
        children_by_parent.setdefault(parent, []).append(pid)
    descendants: set[int] = set()
    stack = list(children_by_parent.get(root_pid, []))
    while stack:
        pid = stack.pop()
        if pid in descendants:
            continue
        descendants.add(pid)
        stack.extend(children_by_parent.get(pid, []))
    return descendants


def _is_python_process(proc: dict[str, Any]) -> bool:
    name = str(proc.get("Name") or "").lower()
    command = str(proc.get("CommandLine") or "").lower()
    process_name = Path(name).name
    if process_name.startswith(("python", "pythonw")) or process_name == "py.exe":
        return True
    stripped = command.strip()
    if not stripped:
        return False
    if stripped.startswith('"'):
        executable = stripped.split('"', 2)[1] if '"' in stripped[1:] else stripped.strip('"')
    else:
        executable = stripped.split(maxsplit=1)[0]
    executable_name = Path(executable).name.lower()
    return executable_name.startswith(("python", "pythonw")) or executable_name == "py.exe"


def _working_set_mb(proc: dict[str, Any]) -> float:
    try:
        return float(proc.get("WorkingSetSize") or 0) / (1024 * 1024)
    except (TypeError, ValueError):
        return 0.0


def run_codex_exec(
    *,
    codex_bin: str,
    workspace: Path,
    runner_dir: Path,
    model: str,
    reasoning_effort: str,
    prompt: str,
    timeout_minutes: int,
    stop_after_report_seconds: int,
    report_pattern: str,
    env_overrides: dict[str, str],
    ignore_user_config: bool,
    codex_hook_policy_script: str | None,
    bypass_approvals_and_sandbox: bool,
) -> dict[str, Any]:
    out_path = runner_dir / "codex_output.jsonl"
    raw_path = runner_dir / "codex_stdout.log"
    err_path = runner_dir / "codex_error.log"
    final_message_path = runner_dir / "final_message.txt"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    command = resolve_codex_command(codex_bin) + [
        "-a",
        "never",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-rules",
        "--json",
        "-C",
        str(workspace),
        "-m",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        "-c",
        'shell_environment_policy.inherit="all"',
        "-o",
        str(final_message_path),
    ]
    if bypass_approvals_and_sandbox:
        command.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        command.extend(
            [
                "--sandbox",
                "workspace-write",
                "-c",
                "sandbox_workspace_write.network_access=true",
            ]
        )
    if codex_hook_policy_script:
        hook_command = f'"{sys.executable}" "{codex_hook_policy_script}"'
        hook_specs = [
            ("PreToolUse", "Checking playground tool policy"),
            ("PermissionRequest", "Checking playground permission policy"),
            ("PostToolUse", "Recording playground tool result"),
        ]
        command.extend(["--enable", "hooks", "--dangerously-bypass-hook-trust"])
        for event_name, status_message in hook_specs:
            hook_value = (
                "[{"
                'matcher="*",'
                "hooks=[{"
                'type="command",'
                f"command={json.dumps(hook_command)},"
                "timeout=5,"
                f"statusMessage={json.dumps(status_message)}"
                "}]"
                "}]"
            )
            command.extend(["-c", f"hooks.{event_name}={hook_value}"])
    if ignore_user_config:
        command.append("--ignore-user-config")
    command.append("-")

    env = os.environ.copy()
    env.update(env_overrides)
    env.setdefault("CODEX_DISABLE_NONESSENTIAL_TRAFFIC", "1")

    started = time.time()
    process_cleanup_events: list[dict[str, Any]] = []
    helper_first_seen: dict[int, float] = {}
    seen_helper_pids: set[int] = set()
    seen_helper_signatures: dict[int, tuple[str, str]] = {}
    helper_limit_reported: set[int] = set()
    helper_timeout_seconds = int(env.get("PLAYGROUND_HELPER_TIMEOUT_SECONDS", "60") or "60")
    helper_watchdog_seconds = max(helper_timeout_seconds + 15, 75)
    helper_memory_limit_mb = 2048.0

    process = subprocess.Popen(
        command,
        cwd=workspace,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(prompt)
    process.stdin.close()

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

    def kill_process_tree(pid: int, reason: str) -> None:
        if os.name == "nt":
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            try:
                os.kill(pid, 9)
                return_code = 0
            except OSError:
                return_code = 1
            completed = subprocess.CompletedProcess(["kill", str(pid)], return_code)
        process_cleanup_events.append(
            {
                "pid": pid,
                "reason": reason,
                "return_code": completed.returncode,
            }
        )

    def watch_descendant_helpers() -> None:
        if os.name != "nt" or process.poll() is not None:
            return
        try:
            processes = _windows_process_table()
        except Exception as exc:
            process_cleanup_events.append({"reason": "watchdog_scan_failed", "error": repr(exc)})
            return
        descendants = _descendant_pids(process.pid, processes)
        by_pid: dict[int, dict[str, Any]] = {}
        for proc in processes:
            try:
                pid = int(proc.get("ProcessId"))
            except (TypeError, ValueError):
                continue
            by_pid[pid] = proc
        now = time.time()
        for pid in sorted(descendants):
            proc = by_pid.get(pid)
            if not proc or not _is_python_process(proc):
                continue
            seen_helper_pids.add(pid)
            seen_helper_signatures[pid] = (
                str(proc.get("Name") or ""),
                str(proc.get("CommandLine") or ""),
            )
            first_seen = helper_first_seen.setdefault(pid, now)
            age = now - first_seen
            memory_mb = _working_set_mb(proc)
            if age >= helper_watchdog_seconds or memory_mb >= helper_memory_limit_mb:
                if pid in helper_limit_reported:
                    continue
                helper_limit_reported.add(pid)
                command_line = str(proc.get("CommandLine") or "")
                process_cleanup_events.append(
                    {
                        "pid": pid,
                        "reason": "helper_watchdog_limit_observed",
                        "age_sec": round(age, 3),
                        "memory_mb": round(memory_mb, 3),
                        "limit_age_sec": helper_watchdog_seconds,
                        "limit_memory_mb": helper_memory_limit_mb,
                        "command": command_line[:240],
                    }
                )

    def cleanup_seen_helpers(reason: str) -> None:
        if os.name != "nt" or not seen_helper_pids:
            return
        try:
            processes = _windows_process_table()
        except Exception as exc:
            process_cleanup_events.append({"reason": "final_cleanup_scan_failed", "error": repr(exc)})
            return
        live: dict[int, dict[str, Any]] = {}
        for proc in processes:
            try:
                live[int(proc.get("ProcessId"))] = proc
            except (TypeError, ValueError):
                continue
        for pid in sorted(seen_helper_pids & set(live)):
            previous = seen_helper_signatures.get(pid)
            current = (
                str(live[pid].get("Name") or ""),
                str(live[pid].get("CommandLine") or ""),
            )
            if previous is not None and current != previous:
                process_cleanup_events.append(
                    {
                        "pid": pid,
                        "reason": "runner_exit_helper_cleanup_skipped_pid_reuse_guard",
                        "previous": {"name": previous[0], "command": previous[1][:240]},
                        "current": {"name": current[0], "command": current[1][:240]},
                    }
                )
                continue
            process_cleanup_events.append(
                {
                    "pid": pid,
                    "reason": f"{reason}_observed",
                    "name": current[0],
                    "command": current[1][:240],
                }
            )

    def stop_process_tree() -> None:
        if process.poll() is None:
            kill_process_tree(process.pid, "runner_stop")

    latest = None
    report_first_seen_at = None
    stopped_reason = None
    event_count = 0
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
    last_process_watchdog = 0.0

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
            if event.get("type") == "turn.completed":
                run_usage = event.get("usage", {})
                for key in usage:
                    usage[key] += int(run_usage.get(key, 0) or 0)

        while True:
            try:
                queued = line_queue.get(timeout=1)
            except queue.Empty:
                queued = None

            if queued is sentinel:
                stdout_done = True
            elif isinstance(queued, str):
                record_line(queued)

            if os.name == "nt" and time.time() - last_process_watchdog >= 10:
                last_process_watchdog = time.time()
                watch_descendant_helpers()

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
                    stop_process_tree()

            if stdout_done and process.poll() is not None:
                break

            if time.time() - started >= timeout_minutes * 60:
                stopped_reason = "timeout"
                stop_process_tree()
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
        stop_process_tree()
        return_code = 124
    if stopped_reason == "timeout":
        return_code = 124
    cleanup_seen_helpers("runner_exit_helper_cleanup")
    cleanup_path = runner_dir / "process_cleanup.json"
    cleanup_path.write_text(json.dumps(process_cleanup_events, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "command": command[:-1] + ["<stdin>"],
        "output": str(out_path),
        "raw_output": str(raw_path),
        "error_log": str(err_path),
        "final_message": str(final_message_path),
        "report": str(latest) if latest else None,
        "stopped_reason": stopped_reason,
        "exit_code": return_code,
        "event_count": event_count,
        "usage": usage,
        "wall_clock_sec": round(time.time() - started, 3),
        "process_cleanup": str(cleanup_path),
        "process_cleanup_events": process_cleanup_events,
        "approval_policy": "never",
        "user_config_loaded": not ignore_user_config,
        "sandbox_mode": "danger-full-access" if bypass_approvals_and_sandbox else "workspace-write",
        "sandbox_network_access": not bypass_approvals_and_sandbox,
    }


def run_track(args: argparse.Namespace, track: str, track_config: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    source_root = Path.cwd().resolve()
    label_prefix = "codex-cli"
    report_template = "codex_cli_random_playtest_{track}_{safe_model}_{timestamp}_report.md"
    report_pattern = "codex_cli_random_playtest_*_report.md"
    if args.harness_profile != "codex-default":
        profile_fragment = common.safe_fragment(args.harness_profile)
        label_prefix = f"codex-cli-{profile_fragment}"
        report_template = f"codex_cli_{profile_fragment}_random_playtest_{{track}}_{{safe_model}}_{{timestamp}}_report.md"
        report_pattern = f"codex_cli_{profile_fragment}_random_playtest_*_report.md"
    ignore_user_config = bool(args.ignore_user_config or (args.bypass_approvals_and_sandbox and not args.keep_user_config))
    prepared = common.prepare_track_run(
        source_root=source_root,
        runner="codex-cli",
        runner_client="Codex CLI",
        model=args.model,
        reasoning_variant=args.reasoning_effort,
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
    safe_model = prepared["safe_model"]
    task_id = prepared["task_id"]
    tick_budget = int(prepared["tick_budget"])
    soft_stop_tick = prepared.get("soft_stop_tick")
    soft_stop_display = "disabled" if soft_stop_tick is None else str(int(soft_stop_tick))
    profile_prompt = harness_profile_prompt(args.harness_profile)
    prompt = (
        "The complete playtest prompt is included below. Do not search for a prompt file; "
        "use the instructions in this message as the authoritative task.\n"
        "Do not inspect, print, manually set, or store runner auth environment variables; "
        "the SDK reads them automatically.\n\n"
        + (profile_prompt + "\n\n" if profile_prompt else "")
        + prepared["prompt"]
    )
    server_url = prepared["server_url"]
    metadata_path = Path(prepared["metadata"])
    metadata = common.load_json(metadata_path)
    metadata.update({
        "reasoning_effort": args.reasoning_effort,
        "timeout_minutes": args.timeout_minutes,
        "prompt_delivery": "stdin_message",
        "harness_profile": args.harness_profile,
        "codex_approval_policy": "never",
        "codex_user_config_loaded": not ignore_user_config,
        "codex_sandbox_mode": "danger-full-access" if args.bypass_approvals_and_sandbox else "workspace-write",
        "codex_sandbox_network_access": not args.bypass_approvals_and_sandbox,
    })
    (runner_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"RUN_DIR={run_dir}")
    print(
        f"TRACK={track} MODEL={args.model} REASONING={args.reasoning_effort} "
        f"BUDGET={tick_budget} SOFT_STOP={soft_stop_display}"
    )
    server_url_env = str(prepared.get("server_url_env") or "ARCANE_LAB_SERVER_URL")
    auth_token_env = str(prepared.get("auth_token_env") or "ARCANE_LAB_AUTH_TOKEN")
    env_overrides = {
        server_url_env: server_url,
        auth_token_env: str(prepared["auth_token"]),
    }
    helper_guard_path = str(prepared.get("python_helper_guard_path") or "")
    helper_timeout_seconds = int(prepared.get("python_helper_timeout_seconds") or common.DEFAULT_HELPER_TIMEOUT_SECONDS)
    if helper_guard_path:
        existing_pythonpath = os.environ.get("PYTHONPATH", "")
        env_overrides["PYTHONPATH"] = (
            helper_guard_path
            if not existing_pythonpath
            else helper_guard_path + os.pathsep + existing_pythonpath
        )
        env_overrides["PLAYGROUND_HELPER_TIMEOUT_SECONDS"] = str(helper_timeout_seconds)
    practice_auth_token_env = str(prepared.get("practice_auth_token_env") or "")
    if prepared.get("practice_auth_token") and practice_auth_token_env:
        env_overrides[practice_auth_token_env] = str(prepared["practice_auth_token"])
    data_path_env = str(prepared.get("data_path_env") or "")
    if prepared.get("workspace_data_path") and data_path_env:
        env_overrides[data_path_env] = str(prepared["workspace_data_path"])
    if prepared.get("env_id", "arcane_lab") == "arcane_lab":
        env_overrides["ARCANE_LAB_CRIT_MODE"] = str(prepared.get("token_crit_mode") or prepared.get("crit_mode") or "random")
    if prepared.get("token_crit_charge_bonus") is not None:
        env_overrides["ARCANE_LAB_CRIT_CHARGE_BONUS"] = str(prepared["token_crit_charge_bonus"])
    if prepared.get("token_crit_random_chance") is not None:
        env_overrides["ARCANE_LAB_CRIT_RANDOM_CHANCE"] = str(prepared["token_crit_random_chance"])
    if prepared.get("token_crit_random_bonus") is not None:
        env_overrides["ARCANE_LAB_CRIT_RANDOM_BONUS"] = str(prepared["token_crit_random_bonus"])
    codex_hook_policy_script = str(prepared.get("codex_hook_policy_script") or "")
    codex_hook_log_path = str(prepared.get("codex_hook_log_path") or "")
    if codex_hook_log_path:
        env_overrides["PLAYGROUND_CODEX_HOOK_LOG"] = codex_hook_log_path

    codex_result = run_codex_exec(
        codex_bin=args.codex_bin,
        workspace=run_dir,
        runner_dir=runner_dir,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        prompt=prompt,
        timeout_minutes=args.timeout_minutes,
        stop_after_report_seconds=args.stop_after_report_seconds,
        report_pattern=report_pattern,
        env_overrides=env_overrides,
        ignore_user_config=ignore_user_config,
        codex_hook_policy_script=codex_hook_policy_script or None,
        bypass_approvals_and_sandbox=args.bypass_approvals_and_sandbox,
    )

    summary = common.build_track_summary(
        source_root=source_root,
        metadata_path=metadata_path,
        output_path=Path(codex_result["output"]),
        report_path=Path(codex_result["report"]) if codex_result["report"] else None,
        stopped_reason=codex_result["stopped_reason"],
        exit_code=codex_result["exit_code"],
        extra={
            "reasoning_effort": args.reasoning_effort,
            "harness_profile": args.harness_profile,
            "raw_output": codex_result["raw_output"],
            "final_message": codex_result["final_message"],
            "event_count": codex_result["event_count"],
            "usage": codex_result["usage"],
            "wall_clock_sec": codex_result["wall_clock_sec"],
            "process_cleanup": codex_result["process_cleanup"],
            "process_cleanup_events": codex_result["process_cleanup_events"],
            "codex_hook_log": codex_hook_log_path or None,
            "codex_approval_policy": codex_result["approval_policy"],
            "codex_user_config_loaded": codex_result["user_config_loaded"],
            "codex_sandbox_mode": codex_result["sandbox_mode"],
            "codex_sandbox_network_access": codex_result["sandbox_network_access"],
        },
    )
    (runner_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Arcane Lab tracks through Codex CLI.")
    parser.add_argument("--model", default="gpt-5.3-codex-spark")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--track-config-path", default="envs/arcane_lab/docs/tracks/config.json")
    parser.add_argument("--track", action="append", help="Track to run. Repeatable. Overrides the default suite when used.")
    parser.add_argument("--suite", action="append", help="Configured track suite to run. Repeatable. Defaults to config default_suite.")
    parser.add_argument("--list-tracks", action="store_true", help="Print configured tracks and suites, then exit.")
    parser.add_argument("--shared-prompt-path", default="")
    parser.add_argument("--prompt-path", default="")
    parser.add_argument("--out-dir", default="agent_workspaces/codex_cli_runs")
    parser.add_argument("--tick-budget", type=int)
    parser.add_argument("--timeout-minutes", type=int, default=60)
    parser.add_argument("--stop-after-report-seconds", type=int, default=45)
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument(
        "--keep-user-config",
        action="store_true",
        help="Keep the normal Codex user config even in yolo mode. Sandbox mode already keeps it by default.",
    )
    parser.add_argument(
        "--ignore-user-config",
        action="store_true",
        help="Force Codex --ignore-user-config. On this Windows host it can make workspace-write reject Python helpers.",
    )
    parser.add_argument(
        "--bypass-approvals-and-sandbox",
        action="store_true",
        help="Use Codex yolo mode. Dangerous; default is workspace-write sandbox with network access for the local game server.",
    )
    parser.add_argument(
        "--harness-profile",
        choices=["codex-default", "opencode-like"],
        default="codex-default",
        help="Optional behavior shim. `opencode-like` keeps the same task prompt but nudges Codex toward OpenCode-style bounded route-file work.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.keep_user_config and args.ignore_user_config:
        raise SystemExit("--keep-user-config and --ignore-user-config are mutually exclusive")
    source_root = Path.cwd().resolve()
    config = common.load_json(common.resolve_source_path(source_root, args.track_config_path))
    tracks = config["tracks"]
    if args.list_tracks:
        print(json.dumps({
            "default_suite": config.get("default_suite"),
            "suites": config.get("suites", {}),
            "tracks": list(tracks.keys()),
        }, indent=2, ensure_ascii=False))
        return 0
    try:
        selected = common.resolve_track_selection(
            config,
            requested_tracks=args.track,
            requested_suites=args.suite,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    summaries = []
    for track in selected:
        summaries.append(run_track(args, track, tracks[track], config))
    result_root = source_root / args.out_dir
    result_root.mkdir(parents=True, exist_ok=True)
    matrix_path = result_root / f"codex_cli_matrix_{time.strftime('%Y%m%d_%H%M%S')}.json"
    matrix_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MATRIX_SUMMARY={matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
