from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, TextIO

import runner_common as common


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def resolve_reasonix_command(reasonix_bin: str, reasonix_package: str) -> list[str]:
    candidate = Path(reasonix_bin)
    if candidate.exists():
        command = [str(candidate)]
    else:
        command = [reasonix_bin]
        for name in (f"{reasonix_bin}.cmd", f"{reasonix_bin}.exe", reasonix_bin):
            resolved = shutil.which(name)
            if resolved:
                command = [resolved]
                break

    executable = Path(command[0]).name.lower()
    if executable in {"npx", "npx.cmd", "npx.exe"}:
        return command + ["-y", reasonix_package]
    return command


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


def reasonix_config_path() -> Path:
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    return (Path(home) if home else Path.home()) / ".reasonix" / "config.json"


def snapshot_reasonix_config(enabled: bool) -> dict[str, Any] | None:
    if not enabled:
        return None
    path = reasonix_config_path()
    if path.exists():
        return {"path": str(path), "exists": True, "data": path.read_bytes()}
    return {"path": str(path), "exists": False, "data": b""}


def restore_reasonix_config(snapshot: dict[str, Any] | None) -> bool:
    if not snapshot:
        return False
    path = Path(str(snapshot["path"]))
    if snapshot.get("exists"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(snapshot["data"])
    elif path.exists():
        path.unlink()
    return True


def scrub_command(command: list[str]) -> list[str]:
    scrubbed: list[str] = []
    skip_next = False
    for item in command:
        if skip_next:
            scrubbed.append("<path>")
            skip_next = False
            continue
        scrubbed.append(item)
        if item in {"--transcript", "--dir"}:
            skip_next = True
    return scrubbed


def permission_should_reject(params: dict[str, Any]) -> bool:
    payload = json.dumps(params, ensure_ascii=False, sort_keys=True).lower()
    hard_denies = [
        "taskkill",
        "stop-process",
        "kill -9",
        "rm -rf",
        "rmdir /s",
        "del /s",
        "format ",
        "shutdown",
    ]
    if any(needle in payload for needle in hard_denies):
        return True
    return "remove-item" in payload and "-recurse" in payload


class ReasonixAcpClient:
    def __init__(
        self,
        *,
        process: subprocess.Popen[str],
        raw_handle: TextIO,
        err_handle: TextIO,
        protocol_handle: TextIO,
    ) -> None:
        self.process = process
        self.raw_handle = raw_handle
        self.err_handle = err_handle
        self.protocol_handle = protocol_handle
        self._send_lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._state = threading.Condition()
        self._next_id = 1
        self._responses: dict[int, dict[str, Any]] = {}
        self.stdout_done = False
        self.stderr_done = False
        self.event_count = 0
        self.tool_event_count = 0
        self.permission_requests: list[dict[str, Any]] = []
        self.agent_message_chunks: list[str] = []

    def start(self) -> None:
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def send_request(self, method: str, params: dict[str, Any]) -> int:
        with self._send_lock:
            request_id = self._next_id
            self._next_id += 1
            self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}, "send")
            return request_id

    def close_stdin(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
        except OSError:
            pass

    def pop_response(self, request_id: int) -> dict[str, Any] | None:
        with self._state:
            return self._responses.pop(request_id, None)

    def wait_response(self, request_id: int, timeout_seconds: float) -> dict[str, Any] | None:
        deadline = time.time() + timeout_seconds
        with self._state:
            while request_id not in self._responses:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self._state.wait(timeout=remaining)
            return self._responses.pop(request_id)

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                self.raw_handle.write(line)
                self.raw_handle.flush()
                self._handle_incoming(line)
        finally:
            with self._state:
                self.stdout_done = True
                self._state.notify_all()

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        try:
            for line in self.process.stderr:
                self.err_handle.write(line)
                self.err_handle.flush()
        finally:
            self.stderr_done = True

    def _handle_incoming(self, line: str) -> None:
        stripped = line.strip()
        if not stripped:
            return
        try:
            message = json.loads(stripped)
        except json.JSONDecodeError:
            self._log("recv_parse_error", {"line": stripped[:1000]})
            return
        if not isinstance(message, dict):
            self._log("recv_parse_error", {"line": stripped[:1000]})
            return
        self._log("recv", message)
        self.event_count += 1

        method = message.get("method")
        if isinstance(method, str) and message.get("id") is not None:
            self._handle_server_request(message)
            return
        if message.get("id") is not None and method is None:
            try:
                request_id = int(message["id"])
            except (TypeError, ValueError):
                return
            with self._state:
                self._responses[request_id] = message
                self._state.notify_all()
            return
        if isinstance(method, str):
            self._record_notification(method, message.get("params"))

    def _handle_server_request(self, message: dict[str, Any]) -> None:
        method = str(message.get("method") or "")
        request_id = message.get("id")
        params = message.get("params")
        if method == "session/request_permission" and isinstance(params, dict):
            result = self._permission_result(params)
            self._write({"jsonrpc": "2.0", "id": request_id, "result": result}, "send_response")
            return
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"method not handled by runner: {method}"},
            },
            "send_response",
        )

    def _permission_result(self, params: dict[str, Any]) -> dict[str, Any]:
        options = params.get("options")
        if not isinstance(options, list):
            options = []
        rejected = permission_should_reject(params)
        preferred = "reject_once" if rejected else "allow_once"
        fallback = "allow_always" if not rejected else "reject"
        selected = None
        for option in options:
            if isinstance(option, dict) and option.get("kind") == preferred:
                selected = option
                break
        if selected is None:
            for option in options:
                if isinstance(option, dict) and option.get("kind") == fallback:
                    selected = option
                    break
        if selected is None and options:
            selected = next((option for option in options if isinstance(option, dict)), None)

        decision = {
            "rejected": rejected,
            "selected_option": selected.get("optionId") if isinstance(selected, dict) else None,
            "title": (((params.get("toolCall") or {}) if isinstance(params.get("toolCall"), dict) else {}).get("title")),
        }
        self.permission_requests.append(decision)
        if not isinstance(selected, dict) or not selected.get("optionId"):
            return {"outcome": {"outcome": "cancelled"}}
        return {"outcome": {"outcome": "selected", "optionId": selected["optionId"]}}

    def _record_notification(self, method: str, params: Any) -> None:
        if method != "session/update" or not isinstance(params, dict):
            return
        update = params.get("update")
        if not isinstance(update, dict):
            return
        kind = update.get("sessionUpdate")
        if kind == "tool_call":
            self.tool_event_count += 1
        if kind != "agent_message_chunk":
            return
        content = update.get("content")
        if isinstance(content, dict) and isinstance(content.get("text"), str):
            self.agent_message_chunks.append(content["text"])

    def _write(self, message: dict[str, Any], direction: str) -> None:
        assert self.process.stdin is not None
        line = json.dumps(message, ensure_ascii=False)
        self._log(direction, message)
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def _log(self, direction: str, message: dict[str, Any]) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "direction": direction,
            "message": message,
        }
        with self._log_lock:
            self.protocol_handle.write(json.dumps(record, ensure_ascii=True) + "\n")
            self.protocol_handle.flush()


def response_result(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("error"):
        error = response["error"]
        if isinstance(error, dict):
            raise RuntimeError(str(error.get("message") or error))
        raise RuntimeError(str(error))
    result = response.get("result")
    return result if isinstance(result, dict) else {}


def transcript_stats(path: Path) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "tool_calls": 0,
        "cost_usd": 0.0,
        "models": [],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 0,
        },
        "final_message": "",
    }
    models: set[str] = set()
    if not path.exists():
        return stats
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        role = event.get("role")
        if role == "tool":
            stats["tool_calls"] += 1
        if role == "assistant_final" and isinstance(event.get("content"), str):
            stats["final_message"] = event["content"]
        if isinstance(event.get("model"), str):
            models.add(event["model"])
        usage = event.get("usage")
        if isinstance(usage, dict):
            for key in stats["usage"]:
                stats["usage"][key] += int(usage.get(key, 0) or 0)
        cost = event.get("cost")
        if isinstance(cost, (int, float)):
            stats["cost_usd"] += float(cost)
    stats["cost_usd"] = round(float(stats["cost_usd"]), 6)
    stats["models"] = sorted(models)
    return stats


def run_reasonix_acp(
    *,
    reasonix_bin: str,
    reasonix_package: str,
    workspace: Path,
    runner_dir: Path,
    model: str,
    effort: str,
    message: str,
    timeout_minutes: int,
    stop_after_report_seconds: int,
    report_pattern: str,
    env_overrides: dict[str, str],
    budget_usd: float | None,
    yolo: bool,
    mcp_specs: list[str],
    preserve_reasonix_config: bool,
) -> dict[str, Any]:
    transcript_path = runner_dir / "reasonix_transcript.jsonl"
    protocol_path = runner_dir / "reasonix_protocol.jsonl"
    raw_path = runner_dir / "reasonix_stdout.log"
    err_path = runner_dir / "reasonix_stderr.log"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    command = resolve_reasonix_command(reasonix_bin, reasonix_package) + [
        "acp",
        "--dir",
        str(workspace),
        "-m",
        model,
        "--effort",
        effort,
        "--transcript",
        str(transcript_path),
    ]
    if budget_usd is not None:
        command.extend(["--budget", str(budget_usd)])
    if yolo:
        command.append("--yolo")
    for spec in mcp_specs:
        command.extend(["--mcp", spec])

    env = os.environ.copy()
    for key in list(env):
        if key.startswith("ARCANE_LAB_") or key.startswith("LEDGER_TOWER_"):
            env.pop(key, None)
    env.update(env_overrides)

    config_snapshot = snapshot_reasonix_config(preserve_reasonix_config)
    started = time.time()
    process = subprocess.Popen(
        command,
        cwd=workspace,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    latest = None
    report_first_seen_at = None
    stopped_reason = None
    prompt_result: dict[str, Any] | None = None
    protocol_error = None

    with raw_path.open("w", encoding="utf-8") as raw_handle, err_path.open(
        "w", encoding="utf-8"
    ) as err_handle, protocol_path.open("w", encoding="utf-8") as protocol_handle:
        client = ReasonixAcpClient(
            process=process,
            raw_handle=raw_handle,
            err_handle=err_handle,
            protocol_handle=protocol_handle,
        )
        client.start()
        try:
            initialize_id = client.send_request(
                "initialize",
                {
                    "protocolVersion": 1,
                    "clientInfo": {"name": "playground-runner", "version": "1"},
                    "clientCapabilities": {},
                },
            )
            initialize_response = client.wait_response(initialize_id, timeout_seconds=45)
            if initialize_response is None:
                stopped_reason = "initialize_timeout"
                stop_process_tree(process)
            else:
                response_result(initialize_response)
                session_id = client.send_request("session/new", {"cwd": str(workspace)})
                session_response = client.wait_response(session_id, timeout_seconds=90)
                if session_response is None:
                    stopped_reason = "session_new_timeout"
                    stop_process_tree(process)
                else:
                    session = response_result(session_response)
                    reasonix_session_id = str(session.get("sessionId") or "")
                    prompt_id = client.send_request(
                        "session/prompt",
                        {
                            "sessionId": reasonix_session_id,
                            "prompt": [{"type": "text", "text": message}],
                        },
                    )
                    deadline = started + timeout_minutes * 60
                    while True:
                        response = client.pop_response(prompt_id)
                        if response is not None:
                            prompt_result = response_result(response)
                            break

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
                                break

                        if process.poll() is not None and client.stdout_done:
                            stopped_reason = stopped_reason or "process_exit_before_prompt_response"
                            break

                        if time.time() >= deadline:
                            stopped_reason = "timeout"
                            stop_process_tree(process)
                            break

                        time.sleep(1)
        except Exception as exc:  # noqa: BLE001 - runner should report protocol failures.
            protocol_error = str(exc)
            stopped_reason = stopped_reason or "protocol_error"
            stop_process_tree(process)
        finally:
            if process.poll() is None:
                client.close_stdin()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                stop_process_tree(process)
            latest = latest_report(logs_dir, report_pattern) or latest
            event_count = client.event_count
            tool_event_count = client.tool_event_count
            permission_requests = client.permission_requests
            agent_message = "".join(client.agent_message_chunks)

    try:
        return_code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        stop_process_tree(process)
        return_code = 124
    if stopped_reason == "timeout":
        return_code = 124
    config_restored = restore_reasonix_config(config_snapshot)

    return {
        "command": scrub_command(command),
        "output": str(transcript_path),
        "protocol_log": str(protocol_path),
        "raw_output": str(raw_path),
        "error_log": str(err_path),
        "report": str(latest) if latest else None,
        "stopped_reason": stopped_reason,
        "exit_code": return_code,
        "event_count": event_count,
        "tool_event_count": tool_event_count,
        "permission_requests": permission_requests,
        "prompt_result": prompt_result,
        "protocol_error": protocol_error,
        "agent_message_tail": agent_message[-4000:],
        "wall_clock_sec": round(time.time() - started, 3),
        "transcript_stats": transcript_stats(transcript_path),
        "reasonix_config_restored": config_restored,
    }


def build_env_overrides(prepared: dict[str, Any]) -> dict[str, str]:
    server_url_env = str(prepared.get("server_url_env") or "ARCANE_LAB_SERVER_URL")
    auth_token_env = str(prepared.get("auth_token_env") or "ARCANE_LAB_AUTH_TOKEN")
    env_overrides = {
        server_url_env: str(prepared["server_url"]),
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
    return env_overrides


def run_track(args: argparse.Namespace, track: str) -> dict[str, Any]:
    source_root = Path.cwd().resolve()
    label_prefix = "reasonix"
    report_template = "reasonix_random_playtest_{track}_{safe_model}_{timestamp}_report.md"
    report_pattern = "reasonix_random_playtest_*_report.md"
    prepared = common.prepare_track_run(
        source_root=source_root,
        runner="reasonix",
        runner_client="Reasonix ACP",
        model=args.model,
        reasoning_variant=args.effort,
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
    prompt_input_path = runner_dir / "prompt.input.md"
    metadata = common.load_json(metadata_path)
    metadata.update(
        {
            "reasonix_mode": "acp",
            "reasonix_package": args.reasonix_package,
            "effort": args.effort,
            "budget_usd": args.budget_usd,
            "timeout_minutes": args.timeout_minutes,
            "prompt_delivery": "acp_json_rpc",
            "permission_mode": "reasonix_yolo" if args.yolo else "runner_auto_allow_once",
            "preserve_reasonix_config": bool(args.preserve_reasonix_config),
            "prompt_input": str(prompt_input_path),
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt = (
        "The complete playtest prompt is included below. Do not search for a prompt file; "
        "use the instructions in this message as the authoritative task.\n"
        "Do not inspect, print, manually set, or store runner auth environment variables; "
        "the SDK reads them automatically.\n\n"
        + prepared["prompt"]
    )
    prompt_input_path.write_text(prompt, encoding="utf-8")

    soft_stop_display = "disabled" if prepared.get("soft_stop_tick") is None else str(prepared["soft_stop_tick"])
    print(f"RUN_DIR={run_dir}")
    print(f"TRACK={track} MODEL={args.model} EFFORT={args.effort} BUDGET={prepared['tick_budget']} SOFT_STOP={soft_stop_display}")

    if args.prepare_only:
        print(f"RUNNER_DIR={runner_dir}")
        return {
            "runner": "reasonix",
            "prepared": True,
            "track": track,
            "model": args.model,
            "effort": args.effort,
            "run_dir": str(run_dir),
            "runner_dir": str(runner_dir),
            "metadata": str(metadata_path),
        }

    reasonix_result = run_reasonix_acp(
        reasonix_bin=args.reasonix_bin,
        reasonix_package=args.reasonix_package,
        workspace=run_dir,
        runner_dir=runner_dir,
        model=args.model,
        effort=args.effort,
        message=prompt,
        timeout_minutes=args.timeout_minutes,
        stop_after_report_seconds=args.stop_after_report_seconds,
        report_pattern=report_pattern,
        env_overrides=build_env_overrides(prepared),
        budget_usd=args.budget_usd,
        yolo=args.yolo,
        mcp_specs=args.mcp or [],
        preserve_reasonix_config=args.preserve_reasonix_config,
    )

    output_path = Path(reasonix_result["output"])
    if not output_path.exists():
        output_path = Path(reasonix_result["protocol_log"])
    summary = common.build_track_summary(
        source_root=source_root,
        metadata_path=metadata_path,
        output_path=output_path,
        report_path=Path(reasonix_result["report"]) if reasonix_result["report"] else None,
        stopped_reason=reasonix_result["stopped_reason"],
        exit_code=reasonix_result["exit_code"],
        extra={
            "effort": args.effort,
            "budget_usd": args.budget_usd,
            "reasonix_package": args.reasonix_package,
            "reasonix_command": reasonix_result["command"],
            "protocol_log": reasonix_result["protocol_log"],
            "raw_output": reasonix_result["raw_output"],
            "error_log": reasonix_result["error_log"],
            "event_count": reasonix_result["event_count"],
            "tool_event_count": reasonix_result["tool_event_count"],
            "permission_requests": reasonix_result["permission_requests"],
            "prompt_result": reasonix_result["prompt_result"],
            "protocol_error": reasonix_result["protocol_error"],
            "agent_message_tail": reasonix_result["agent_message_tail"],
            "transcript_stats": reasonix_result["transcript_stats"],
            "wall_clock_sec": reasonix_result["wall_clock_sec"],
            "reasonix_config_restored": reasonix_result["reasonix_config_restored"],
            "permission_mode": "reasonix_yolo" if args.yolo else "runner_auto_allow_once",
        },
    )
    (runner_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run game tracks through DeepSeek Reasonix ACP.")
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--effort", choices=["low", "medium", "high", "max"], default="high")
    parser.add_argument("--track-config-path", default="envs/arcane_lab/docs/tracks/config.json")
    parser.add_argument("--track", action="append", help="Track to run. Repeatable. Overrides the default suite when used.")
    parser.add_argument("--suite", action="append", help="Configured suite to run. Defaults to config default_suite.")
    parser.add_argument("--list-tracks", action="store_true")
    parser.add_argument("--shared-prompt-path", default="")
    parser.add_argument("--prompt-path", default="")
    parser.add_argument("--out-dir", default="agent_workspaces/reasonix_runs")
    parser.add_argument("--tick-budget", type=int)
    parser.add_argument("--timeout-minutes", type=int, default=60)
    parser.add_argument("--stop-after-report-seconds", type=int, default=45)
    parser.add_argument("--server-url", default="http://127.0.0.1:8765")
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--reasonix-bin", default="npx")
    parser.add_argument("--reasonix-package", default="reasonix")
    parser.add_argument("--mcp", action="append", help="Reasonix MCP server spec. Repeatable.")
    parser.add_argument("--yolo", action="store_true", help="Pass Reasonix --yolo instead of runner-side allow-once permissions.")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument(
        "--no-preserve-reasonix-config",
        dest="preserve_reasonix_config",
        action="store_false",
        help="Do not restore ~/.reasonix/config.json after Reasonix persists --effort.",
    )
    parser.set_defaults(preserve_reasonix_config=True)
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
    matrix_path = result_root / f"reasonix_matrix_{time.strftime('%Y%m%d_%H%M%S')}.json"
    matrix_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MATRIX_SUMMARY={matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
