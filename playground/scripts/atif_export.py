from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ATIF_SCHEMA_VERSION = "ATIF-v1.4"
EXPORTER_NAME = "playground-atif-exporter"
EXPORTER_VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def now_iso_z() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atif_timestamp(value: Any | None, *, fallback: str | None = None) -> str:
    text = str(value or fallback or now_iso_z()).strip()
    if not text:
        return now_iso_z()
    for fmt in ("%Y%m%d_%H%M%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.replace(microsecond=0).isoformat() + "Z"
    if text.endswith("Z"):
        return text
    if "+" in text[10:] or (len(text) > 10 and "-" in text[10:]):
        return text
    return text + "Z"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def omit_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: omit_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [omit_none(item) for item in value]
    return value


def read_text_if_present(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def path_text(path: Path | None) -> str | None:
    return str(path) if path else None


def resolve_path(value: Any, *, base: Path | None = None) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve()


def prompt_path_from_metadata(metadata: dict[str, Any]) -> Path | None:
    for key in ("prompt_input", "prompt_template"):
        path = resolve_path(metadata.get(key))
        if path and path.exists():
            return path
    runner_dir = resolve_path(metadata.get("runner_dir"))
    if runner_dir:
        for name in ("prompt.input.md", "prompt.md"):
            path = runner_dir / name
            if path.exists():
                return path
    return None


def load_prompt(metadata: dict[str, Any]) -> tuple[str | None, Path | None]:
    path = prompt_path_from_metadata(metadata)
    return read_text_if_present(path), path


def selected_game_paths(summary: dict[str, Any] | None = None, verification_path: Path | None = None) -> tuple[Path | None, Path | None]:
    if verification_path is None and summary:
        verification_path = resolve_path(summary.get("verification_path"))
    trajectory_path = verification_path.with_name("trajectory.json") if verification_path else None
    return trajectory_path if trajectory_path and trajectory_path.exists() else None, verification_path if verification_path and verification_path.exists() else None


def agent_payload(metadata: dict[str, Any], summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or {}
    runner = str(metadata.get("runner") or summary.get("runner") or "playground-agent")
    model = str(metadata.get("model") or summary.get("model") or "")
    version = (
        metadata.get("runner_client")
        or metadata.get("reasonix_package")
        or metadata.get("harness_profile")
        or metadata.get("prompt_delivery")
        or "unknown"
    )
    return omit_none(
        {
            "name": runner,
            "version": str(version),
            "model_name": model or None,
            "extra": {
                "runner_client": metadata.get("runner_client"),
                "reasoning_variant": metadata.get("reasoning_variant")
                or metadata.get("reasoning_effort")
                or metadata.get("effort")
                or summary.get("reasoning_variant"),
                "track": metadata.get("track") or summary.get("track"),
                "env_id": metadata.get("env_id"),
            },
        }
    )


def final_metrics(summary: dict[str, Any] | None, extra: dict[str, Any] | None, total_steps: int) -> dict[str, Any]:
    summary = summary or {}
    extra = extra or {}
    usage = extra.get("usage") if isinstance(extra.get("usage"), dict) else summary.get("usage")
    if not isinstance(usage, dict):
        transcript_stats = extra.get("transcript_stats") if isinstance(extra.get("transcript_stats"), dict) else summary.get("transcript_stats")
        if isinstance(transcript_stats, dict):
            usage = transcript_stats.get("usage") if isinstance(transcript_stats.get("usage"), dict) else {}
            cost_usd = transcript_stats.get("cost_usd")
        else:
            usage = {}
            cost_usd = None
    else:
        cost_usd = extra.get("cost_usd") or summary.get("cost_usd")

    prompt_tokens = (
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("total_prompt_tokens")
    )
    completion_tokens = (
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("total_completion_tokens")
    )
    cached_tokens = (
        usage.get("cached_tokens")
        or usage.get("cached_input_tokens")
        or usage.get("prompt_cache_hit_tokens")
        or usage.get("total_cached_tokens")
    )
    cost_usd = cost_usd or usage.get("cost_usd") or usage.get("total_cost_usd")
    return omit_none(
        {
            "total_prompt_tokens": prompt_tokens,
            "total_completion_tokens": completion_tokens,
            "total_cached_tokens": cached_tokens,
            "total_cost_usd": cost_usd,
            "total_steps": total_steps,
        }
    )


def root_extra(
    *,
    metadata: dict[str, Any],
    summary: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    trajectory_path: Path | None,
    verification_path: Path | None,
    output_path: Path | None,
    report_path: Path | None,
    prompt_path: Path | None,
) -> dict[str, Any]:
    summary = summary or {}
    verification = verification or {}
    return omit_none(
        {
            "exporter": {
                "name": EXPORTER_NAME,
                "version": EXPORTER_VERSION,
                "generated_at": now_iso_z(),
                "schema_source": "Harbor ATIF documentation",
            },
            "playground": {
                "env_id": metadata.get("env_id") or verification.get("env_id") or summary.get("env_id"),
                "track": metadata.get("track") or verification.get("track") or summary.get("track"),
                "task_id": metadata.get("token_task_id") or verification.get("task_id") or summary.get("task_id"),
                "game_id": verification.get("game_id") or summary.get("game_id"),
                "official": verification.get("official") if verification else summary.get("accepted") is not None,
                "reward": verification.get("reward") if verification else summary.get("reward"),
                "outcome": verification.get("outcome") or summary.get("outcome"),
                "goal_achieved": verification.get("goalAchieved") if verification else summary.get("goal_achieved"),
                "trajectory_hash": verification.get("trajectory_hash") or summary.get("trajectory_hash"),
                "source_policy": summary.get("source_policy"),
                "route_quality": summary.get("route_quality"),
                "paths": {
                    "prompt": path_text(prompt_path),
                    "agent_output": path_text(output_path),
                    "report": path_text(report_path),
                    "game_trajectory": path_text(trajectory_path),
                    "verification": path_text(verification_path),
                },
            },
        }
    )


def user_prompt_step(step_id: int, metadata: dict[str, Any], prompt_text: str | None, prompt_path: Path | None) -> dict[str, Any] | None:
    if not prompt_text:
        return None
    return omit_none(
        {
            "step_id": step_id,
            "timestamp": atif_timestamp(metadata.get("timestamp")),
            "source": "user",
            "message": prompt_text,
            "extra": {
                "playground_step_type": "task_prompt",
                "prompt_path": path_text(prompt_path),
            },
        }
    )


def game_init_step(step_id: int, trajectory: dict[str, Any]) -> dict[str, Any] | None:
    entries = trajectory.get("entries") if isinstance(trajectory, dict) else None
    session = trajectory.get("session", {}) if isinstance(trajectory, dict) else {}
    if not entries:
        return None
    first = entries[0]
    observation = first.get("observation") if isinstance(first, dict) else None
    return omit_none(
        {
            "step_id": step_id,
            "timestamp": atif_timestamp(first.get("wall_time") if isinstance(first, dict) else None, fallback=session.get("created_at")),
            "source": "system",
            "message": f"Playground game initialized: {session.get('id') or 'unknown'}",
            "extra": {
                "playground_step_type": "game_init",
                "session": session,
                "observation": observation,
            },
        }
    )


def command_step(step_id: int, entry: dict[str, Any], model: str | None) -> dict[str, Any]:
    command = str(entry.get("command") or "")
    tool_call_id = f"playground_command_{entry.get('index', step_id)}"
    content = str(entry.get("output") or "")
    observation = entry.get("observation")
    return omit_none(
        {
            "step_id": step_id,
            "timestamp": atif_timestamp(entry.get("wall_time")),
            "source": "agent",
            "model_name": model or None,
            "message": f"Execute playground command: {command}",
            "tool_calls": [
                {
                    "tool_call_id": tool_call_id,
                    "function_name": "playground.command",
                    "arguments": {"command": command},
                }
            ],
            "observation": {
                "results": [
                    {
                        "source_call_id": tool_call_id,
                        "content": content,
                        "extra": {
                            "playground_entry_index": entry.get("index"),
                            "reward": entry.get("reward"),
                            "done": entry.get("done"),
                            "observation": observation,
                        },
                    }
                ]
            },
            "extra": {
                "playground_step_type": "game_command",
                "command": command,
                "entry_index": entry.get("index"),
            },
        }
    )


def game_command_steps(start_step_id: int, trajectory: dict[str, Any] | None, model: str | None) -> list[dict[str, Any]]:
    if not trajectory:
        return []
    steps: list[dict[str, Any]] = []
    step_id = start_step_id
    init = game_init_step(step_id, trajectory)
    if init:
        steps.append(init)
        step_id += 1
    for entry in trajectory.get("entries", []):
        command = str(entry.get("command") or "")
        if not command or command.startswith("__"):
            continue
        steps.append(command_step(step_id, entry, model))
        step_id += 1
    return steps


def final_report_step(step_id: int, report_text: str | None, report_path: Path | None, model: str | None, timestamp: str | None) -> dict[str, Any] | None:
    if not report_text:
        return None
    return omit_none(
        {
            "step_id": step_id,
            "timestamp": atif_timestamp(timestamp),
            "source": "agent",
            "model_name": model or None,
            "message": report_text,
            "extra": {
                "playground_step_type": "final_report",
                "report_path": path_text(report_path),
            },
        }
    )


def build_atif_trajectory(
    *,
    metadata: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    trajectory: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
    trajectory_path: Path | None = None,
    verification_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    summary = summary or {}
    prompt_text, prompt_path = load_prompt(metadata)
    report_text = read_text_if_present(report_path)
    model = str(metadata.get("model") or summary.get("model") or "") or None
    session = trajectory.get("session", {}) if isinstance(trajectory, dict) else {}
    session_id = (
        metadata.get("token_task_id")
        or ((verification or {}).get("task_id"))
        or summary.get("task_id")
        or session.get("id")
        or summary.get("game_id")
        or f"playground-{int(time.time())}"
    )

    steps: list[dict[str, Any]] = []
    prompt_step = user_prompt_step(1, metadata, prompt_text, prompt_path)
    if prompt_step:
        steps.append(prompt_step)
    next_step_id = len(steps) + 1
    game_steps = game_command_steps(next_step_id, trajectory, model)
    steps.extend(game_steps)
    next_step_id = len(steps) + 1
    report_step = final_report_step(
        next_step_id,
        report_text,
        report_path,
        model,
        summary.get("verified_at") or (verification or {}).get("verified_at") or (session or {}).get("updated_at"),
    )
    if report_step:
        steps.append(report_step)

    root = {
        "schema_version": ATIF_SCHEMA_VERSION,
        "session_id": str(session_id),
        "agent": agent_payload(metadata, summary),
        "steps": steps,
        "final_metrics": final_metrics(summary, extra, len(steps)),
        "extra": root_extra(
            metadata=metadata,
            summary=summary,
            verification=verification,
            trajectory_path=trajectory_path,
            verification_path=verification_path,
            output_path=output_path,
            report_path=report_path,
            prompt_path=prompt_path,
        ),
    }
    return omit_none(root)


def validate_atif(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != ATIF_SCHEMA_VERSION:
        errors.append(f"schema_version must be {ATIF_SCHEMA_VERSION}")
    if not payload.get("session_id"):
        errors.append("session_id is required")
    agent = payload.get("agent")
    if not isinstance(agent, dict) or not agent.get("name"):
        errors.append("agent.name is required")
    steps = payload.get("steps")
    if not isinstance(steps, list):
        errors.append("steps must be a list")
        return errors
    for expected, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"steps.{expected - 1} must be an object")
            continue
        if step.get("step_id") != expected:
            errors.append(f"steps.{expected - 1}.step_id expected {expected}, got {step.get('step_id')}")
        if step.get("source") not in {"user", "agent", "system"}:
            errors.append(f"steps.{expected - 1}.source must be user, agent, or system")
        if not step.get("timestamp"):
            errors.append(f"steps.{expected - 1}.timestamp is required")
        if "observation" in step:
            call_ids = {
                str(call.get("tool_call_id"))
                for call in step.get("tool_calls", [])
                if isinstance(call, dict) and call.get("tool_call_id")
            }
            for result in step.get("observation", {}).get("results", []):
                source_call_id = str(result.get("source_call_id") or "")
                if source_call_id and call_ids and source_call_id not in call_ids:
                    errors.append(f"steps.{expected - 1}.observation source_call_id {source_call_id!r} has no matching tool call")
    return errors


def load_summary_inputs(summary_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path | None, Path | None, Path | None, Path | None]:
    summary = load_json(summary_path)
    runner_dir = summary_path.parent
    metadata_path = runner_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    output_path = resolve_path(summary.get("output"))
    report_path = resolve_path(summary.get("report"))
    trajectory_path, verification_path = selected_game_paths(summary)
    return summary, metadata, output_path, report_path, trajectory_path, verification_path


def export_from_summary(summary_path: Path, out_path: Path | None = None) -> Path:
    summary, metadata, output_path, report_path, trajectory_path, verification_path = load_summary_inputs(summary_path)
    trajectory = load_json(trajectory_path) if trajectory_path else None
    verification = load_json(verification_path) if verification_path else None
    payload = build_atif_trajectory(
        metadata=metadata,
        summary=summary,
        trajectory=trajectory,
        verification=verification,
        trajectory_path=trajectory_path,
        verification_path=verification_path,
        output_path=output_path,
        report_path=report_path,
        extra=summary,
    )
    out_path = out_path or summary_path.with_name("atif_trajectory.json")
    return write_json(out_path, payload)


def export_from_game(trajectory_path: Path, verification_path: Path | None = None, out_path: Path | None = None) -> Path:
    trajectory = load_json(trajectory_path)
    verification = load_json(verification_path) if verification_path and verification_path.exists() else None
    payload = build_atif_trajectory(
        trajectory=trajectory,
        verification=verification,
        trajectory_path=trajectory_path,
        verification_path=verification_path,
    )
    out_path = out_path or trajectory_path.with_name("atif_trajectory.json")
    return write_json(out_path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Playground runner or game trajectories as Harbor ATIF JSON.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--summary", help="Path to a runner .runner/summary.json file.")
    source.add_argument("--trajectory", help="Path to a server game trajectory.json file.")
    source.add_argument("--game-id", help="Server game id under --games-root.")
    parser.add_argument("--verification", help="Optional verification.json path when using --trajectory.")
    parser.add_argument("--games-root", default="logs/server/games", help="Game root used with --game-id.")
    parser.add_argument("--out", help="Output path. Defaults beside the selected input.")
    parser.add_argument("--validate", action="store_true", help="Run the lightweight local ATIF sanity validator after export.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = resolve_path(args.out) if args.out else None
    if args.summary:
        written = export_from_summary(Path(args.summary).resolve(), out_path)
    else:
        if args.game_id:
            game_dir = Path(args.games_root).resolve() / args.game_id
            trajectory_path = game_dir / "trajectory.json"
            verification_path = game_dir / "verification.json"
        else:
            trajectory_path = Path(args.trajectory).resolve()
            verification_path = Path(args.verification).resolve() if args.verification else trajectory_path.with_name("verification.json")
        written = export_from_game(trajectory_path, verification_path, out_path)

    if args.validate:
        errors = validate_atif(load_json(written))
        if errors:
            for error in errors:
                print(f"ATIF validation error: {error}")
            return 1
    print(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
