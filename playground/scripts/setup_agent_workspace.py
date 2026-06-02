from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_ENVIRONMENT = "arcane_lab"
SERVER_SDK_ITEMS = ("sdk/__init__.py", "sdk/server_sdk.py", "sdk/result.py")
DIRECT_ENGINE_ITEMS = ("game.py", "data", "sdk")

TRACK_DOC_ITEMS = {
    "pure-blind": (),
    "blind-discovery": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md"),
    "visible-goal": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md"),
    "mechanics-check": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md"),
    "budgeted-prestige": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md"),
    "provided-helper-prestige": (
        "README.md",
        "docs/agent-brief.md",
        "docs/sdk-api.md",
        "docs/tasks.md",
        "tools/arcane_practice_helper.py",
    ),
    "warmup-fork-prestige": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md"),
    "route-optimization": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md"),
    "crit-build-eval": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md"),
    "tutorial-clear": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "tools/ledger_submit_route.py"),
    "ledger-clear": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "high-score": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "high-score-whitebox": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "high-score-token-limited": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "high-score-practice-budgeted": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "high-score-best-of-3": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "boss-gated-high-score": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
    "generated-shop-timing-8f-high-score": ("README.md", "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md", "tools/ledger_submit_route.py"),
}

PROFILE_ITEMS = {
    "deepseek-prestige": (*DIRECT_ENGINE_ITEMS, "docs/agent-brief.md", "docs/sdk-api.md", "docs/tasks.md"),
    "deepseek-random": (
        *DIRECT_ENGINE_ITEMS,
        "README.md",
        "docs/agent-brief.md",
        "docs/sdk-api.md",
        "docs/tasks.md",
        "scripts/smoke.txt",
    ),
}


def normalized_item(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def resolve_environment_root(source_root: Path, environment: str = DEFAULT_ENVIRONMENT) -> Path:
    source_root = source_root.resolve()
    if source_root.name == environment:
        return source_root
    candidate = source_root / "envs" / environment
    return candidate if candidate.exists() else source_root


def items_for_profile(profile: str, track: str | None, *, offline_practice: bool = True) -> list[str]:
    if profile == "track":
        if not track:
            raise SystemExit("--track is required when --profile track is used")
        if track not in TRACK_DOC_ITEMS:
            known = ", ".join(sorted(TRACK_DOC_ITEMS))
            raise SystemExit(f"unknown track {track!r}; known tracks: {known}")
        core_items = DIRECT_ENGINE_ITEMS if offline_practice else SERVER_SDK_ITEMS
        return [*core_items, *TRACK_DOC_ITEMS[track]]
    if profile not in PROFILE_ITEMS:
        known = ", ".join(["track", *sorted(PROFILE_ITEMS)])
        raise SystemExit(f"unknown profile {profile!r}; known profiles: {known}")
    return list(PROFILE_ITEMS[profile])


def copy_item(source_root: Path, dest_root: Path, item: str) -> dict[str, Any]:
    item = normalized_item(item)
    source = source_root / item
    destination = dest_root / item
    record: dict[str, Any] = {"item": item, "source": str(source), "destination": str(destination)}
    if not source.exists():
        record["status"] = "missing"
        return record

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        record["kind"] = "directory"
        record["file_count"] = sum(1 for child in destination.rglob("*") if child.is_file())
    else:
        shutil.copy2(source, destination)
        record["kind"] = "file"
        record["bytes"] = destination.stat().st_size
    record["status"] = "copied"
    return record


def setup_workspace(
    *,
    source_root: Path,
    dest_root: Path,
    profile: str,
    track: str | None,
    manifest_out: Path | None,
    offline_practice: bool = True,
    environment: str = DEFAULT_ENVIRONMENT,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    environment_root = resolve_environment_root(source_root, environment)
    dest_root.mkdir(parents=True, exist_ok=True)
    (dest_root / "logs").mkdir(parents=True, exist_ok=True)
    (dest_root / ".runner").mkdir(parents=True, exist_ok=True)

    items = []
    seen: set[str] = set()
    for item in items_for_profile(profile, track, offline_practice=offline_practice):
        normalized = normalized_item(item)
        if normalized not in seen:
            items.append(normalized)
            seen.add(normalized)

    records = [copy_item(environment_root, dest_root, item) for item in items]
    copied = {record["item"] for record in records if record.get("status") == "copied"}
    omitted_candidates = [
        "game.py",
        "data",
        "sdk/arcane_lab_sdk.py",
        "sdk/ledger_tower_sdk.py",
        "server.py",
        "mcp_server.py",
        "logs",
        "saves",
        "agent_workspaces",
        "web_design.png",
        ".where-agent-progress.md",
        "AGENTS.md",
        "scripts/*.txt route answers",
        "scripts/*.py runner and smoke helpers",
    ]
    omitted_by_design = [
        item
        for item in omitted_candidates
        if item not in copied
        and not (item in {"sdk/arcane_lab_sdk.py", "sdk/ledger_tower_sdk.py"} and "sdk" in copied)
    ]

    manifest = {
        "source_root": str(source_root),
        "environment": environment,
        "environment_root": str(environment_root),
        "workspace": str(dest_root),
        "profile": profile,
        "track": track,
        "offline_practice": offline_practice if profile == "track" else None,
        "workspace_mode": "direct-sdk" if profile != "track" or offline_practice else "server-only",
        "items": records,
        "omitted_by_design": omitted_by_design,
        "note": (
            "track workspace mode is configurable. direct-sdk mode includes the local engine for "
            "offline direct SDK practice; server-only mode includes only server SDK files. "
            "Both modes omit the replay server, runner scripts, historical logs, and route-answer scripts."
        ),
    }

    if manifest_out:
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a lean playground agent workspace.")
    parser.add_argument("--source-root", default=".", help="Arcane Lab source workspace root.")
    parser.add_argument("--env", default=DEFAULT_ENVIRONMENT, help="Game environment id under envs/.")
    parser.add_argument("--dest", required=True, help="Destination agent workspace.")
    parser.add_argument("--profile", default="track", help="Workspace profile: track, deepseek-prestige, deepseek-random.")
    parser.add_argument("--track", default=None, help="Track name when profile=track.")
    parser.add_argument(
        "--offline-practice",
        choices=("true", "false"),
        default="true",
        help="When profile=track, include the direct local engine for offline ArcaneLabSDK practice.",
    )
    parser.add_argument("--manifest-out", default=None, help="Optional JSON manifest path.")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    dest_root = Path(args.dest).resolve()
    manifest_out = Path(args.manifest_out).resolve() if args.manifest_out else None
    manifest = setup_workspace(
        source_root=source_root,
        dest_root=dest_root,
        profile=args.profile,
        track=args.track,
        manifest_out=manifest_out,
        offline_practice=args.offline_practice == "true",
        environment=args.env,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
