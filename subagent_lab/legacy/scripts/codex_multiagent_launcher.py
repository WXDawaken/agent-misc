#!/usr/bin/env python3
"""Launch role-scoped Codex sessions from repo-local multi-agent config."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover - Python < 3.11
    raise SystemExit("Python 3.11+ is required because tomllib is unavailable.") from exc


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "codex.multiagent.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch a Codex role using repo-local multi-agent workflow and runtime profile TOML files."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Target workspace for the Codex session. Required unless --list-roles is used.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to the multi-agent workflow TOML file.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        help="Optional override path for the runtime profile catalog TOML file.",
    )
    parser.add_argument(
        "--role",
        help="Role to launch. Defaults to the workflow entry_role.",
    )
    parser.add_argument(
        "--message",
        help="Operator request appended to the role prompt.",
    )
    parser.add_argument(
        "--message-file",
        type=Path,
        help="Path to a text file whose contents are appended to the role prompt.",
    )
    parser.add_argument(
        "--list-roles",
        action="store_true",
        help="List available roles with resolved runtime profiles and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve inputs and print the command without launching Codex.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the fully rendered prompt to stdout.",
    )
    parser.add_argument(
        "--exec",
        dest="use_exec",
        action="store_true",
        help="Use `codex exec` instead of launching the interactive TUI.",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        type=Path,
        help="Additional writable directories forwarded to Codex. Repeatable.",
    )
    parser.add_argument(
        "--codex-bin",
        default="codex",
        help="Codex executable name or absolute path.",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Enable Codex web search.",
    )
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Forward Codex full-auto mode.",
    )
    parser.add_argument(
        "--profile",
        dest="codex_profile",
        help="Forward a Codex config profile name.",
    )
    parser.add_argument(
        "--oss",
        action="store_true",
        help="Use the local open-source provider.",
    )
    parser.add_argument(
        "--local-provider",
        help="Forward the Codex local provider name.",
    )
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        type=Path,
        help="Attach image files to the initial prompt. Repeatable.",
    )
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        help="Enable a Codex feature flag. Repeatable.",
    )
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        help="Disable a Codex feature flag. Repeatable.",
    )
    parser.add_argument(
        "--no-alt-screen",
        action="store_true",
        help="Disable alternate screen mode for interactive Codex runs.",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Run `codex exec` without persisting session files.",
    )
    parser.add_argument(
        "--skip-git-repo-check",
        action="store_true",
        help="Forward `--skip-git-repo-check` to `codex exec`.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print `codex exec` events as JSONL.",
    )
    parser.add_argument(
        "--progress-cursor",
        action="store_true",
        help="Force cursor-based progress updates in `codex exec`.",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        help="Forward `--color` to `codex exec`.",
    )
    parser.add_argument(
        "--output-last-message",
        type=Path,
        help="Write the last agent message to this file in `codex exec` mode.",
    )
    parser.add_argument(
        "--output-schema",
        type=Path,
        help="Path to a JSON Schema file for `codex exec` output.",
    )
    return parser.parse_args()


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def resolve_path(path: Path, base_dir: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def validate_mode_specific_args(args: argparse.Namespace) -> None:
    exec_only = {
        "--ephemeral": args.ephemeral,
        "--skip-git-repo-check": args.skip_git_repo_check,
        "--json": args.json,
        "--progress-cursor": args.progress_cursor,
        "--color": args.color is not None,
        "--output-last-message": args.output_last_message is not None,
        "--output-schema": args.output_schema is not None,
    }
    interactive_only = {
        "--no-alt-screen": args.no_alt_screen,
    }

    if not args.use_exec:
        invalid = [name for name, enabled in exec_only.items() if enabled]
        if invalid:
            joined = ", ".join(invalid)
            raise SystemExit(f"These flags require --exec: {joined}")

    if args.use_exec:
        invalid = [name for name, enabled in interactive_only.items() if enabled]
        if invalid:
            joined = ", ".join(invalid)
            raise SystemExit(f"These flags are only valid without --exec: {joined}")


def find_codex(binary: str) -> str:
    resolved = shutil.which(binary)
    if resolved:
        return resolved
    raise SystemExit(f"Unable to find Codex executable: {binary}")


def read_message(args: argparse.Namespace) -> str:
    if args.message and args.message_file:
        raise SystemExit("Use either --message or --message-file, not both.")
    if args.message_file:
        path = resolve_path(args.message_file, Path.cwd())
        if not path.is_file():
            raise SystemExit(f"Message file does not exist: {path}")
        return path.read_text(encoding="utf-8").strip()
    if args.message:
        return args.message.strip()
    return ""


def resolve_model(profile: dict, defaults: dict) -> str:
    for key in ("model", "preferred_model", "preferred_model_id", "preferred_model_family"):
        value = profile.get(key)
        if value:
            return value
    model = defaults.get("model")
    if model:
        return model
    raise SystemExit("No model could be resolved from runtime profile or defaults.")


def resolve_role(args: argparse.Namespace, workflow: dict) -> str:
    if args.role:
        return args.role
    role = workflow.get("multiagent", {}).get("entry_role")
    if not role:
        raise SystemExit("Workflow config is missing multiagent.entry_role.")
    return role


def build_prompt(
    role_name: str,
    role_prompt_path: Path,
    role_prompt_text: str,
    runtime_profile_name: str,
    runtime_profile: dict,
    resolved_model_hint: str,
    workflow_path: Path,
    profiles_path: Path,
    workspace: Path,
    shared_context: list[str],
    operator_message: str,
) -> str:
    lines = [role_prompt_text.strip(), "", "[Launcher Context]"]
    lines.append(f"- role: {role_name}")
    lines.append(f"- workspace: {workspace}")
    lines.append(f"- workflow_config: {workflow_path}")
    lines.append(f"- profile_catalog: {profiles_path}")
    lines.append(f"- role_prompt_file: {role_prompt_path}")
    lines.append(f"- runtime_profile: {runtime_profile_name}")
    lines.append(f"- resolved_model_hint: {resolved_model_hint}")
    if runtime_profile.get("preferred_model_tier"):
        lines.append(f"- preferred_model_tier: {runtime_profile['preferred_model_tier']}")
    if runtime_profile.get("model_reasoning_effort"):
        lines.append(f"- model_reasoning_effort: {runtime_profile['model_reasoning_effort']}")
    if runtime_profile.get("selection_bias"):
        lines.append(f"- selection_bias: {runtime_profile['selection_bias']}")
    if shared_context:
        lines.append("- read these shared context files first if they exist:")
        for relative_path in shared_context:
            lines.append(f"  - {workspace / relative_path}")

    lines.extend(["", "[Operator Request]"])
    if operator_message:
        lines.append(operator_message)
    else:
        lines.append(
            "Read the shared context files first, then operate strictly within the selected role contract."
        )

    return "\n".join(lines).strip() + "\n"


def print_role_listing(workflow: dict, profiles: dict, workflow_path: Path, profiles_path: Path) -> int:
    defaults = workflow.get("defaults", {})
    role_table = workflow.get("roles", {})
    profile_table = profiles.get("runtime_profiles", {})

    print(f"workflow: {workflow_path}")
    print(f"profiles: {profiles_path}")
    print("roles:")

    for role_name in sorted(role_table.keys()):
        role_cfg = role_table[role_name]
        profile_name = role_cfg.get("runtime_profile", "<none>")
        profile_cfg = profile_table.get(profile_name, {})
        model = resolve_model(profile_cfg, defaults) if profile_cfg else defaults.get("model", "<unset>")
        effort = profile_cfg.get("model_reasoning_effort", defaults.get("model_reasoning_effort", "<unset>"))
        prompt_file = role_cfg.get("prompt_file", "<unset>")
        print(
            f"  - {role_name}: profile={profile_name} model={model} effort={effort} prompt={prompt_file}"
        )

    return 0


def main() -> int:
    args = parse_args()
    validate_mode_specific_args(args)

    workflow_path = resolve_path(args.config, Path.cwd())
    if not workflow_path.is_file():
        raise SystemExit(f"Workflow config does not exist: {workflow_path}")

    workflow = load_toml(workflow_path)
    runtime_resolution = workflow.get("runtime_resolution", {})
    profiles_setting = args.profiles or Path(runtime_resolution.get("profile_catalog", "codex.profiles.toml"))
    profiles_path = resolve_path(profiles_setting, workflow_path.parent)
    if not profiles_path.is_file():
        raise SystemExit(f"Runtime profile catalog does not exist: {profiles_path}")

    profiles = load_toml(profiles_path)

    if args.list_roles:
        return print_role_listing(workflow, profiles, workflow_path, profiles_path)

    if not args.workspace:
        raise SystemExit("--workspace is required unless --list-roles is used.")

    workspace = resolve_path(args.workspace, Path.cwd())
    if not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist or is not a directory: {workspace}")

    role_name = resolve_role(args, workflow)
    role_table = workflow.get("roles", {})
    role_cfg = role_table.get(role_name)
    if not role_cfg:
        raise SystemExit(f"Unknown role: {role_name}")

    prompt_setting = role_cfg.get("prompt_file")
    if not prompt_setting:
        raise SystemExit(f"Role {role_name} is missing prompt_file.")
    prompt_path = resolve_path(Path(prompt_setting), workflow_path.parent)
    if not prompt_path.is_file():
        raise SystemExit(f"Prompt file does not exist: {prompt_path}")

    profile_name = role_cfg.get("runtime_profile")
    if runtime_resolution.get("require_explicit_profile", False) and not profile_name:
        raise SystemExit(f"Role {role_name} is missing runtime_profile.")

    profile_table = profiles.get(runtime_resolution.get("profile_namespace", "runtime_profiles"), {})
    profile_cfg = profile_table.get(profile_name or "", {})
    if profile_name and not profile_cfg:
        raise SystemExit(f"Runtime profile {profile_name} was not found in {profiles_path}")

    defaults = workflow.get("defaults", {})
    model = resolve_model(profile_cfg, defaults)
    reasoning_effort = profile_cfg.get("model_reasoning_effort", defaults.get("model_reasoning_effort"))
    approval_policy = profile_cfg.get("approval_policy", defaults.get("approval_policy"))
    sandbox_mode = profile_cfg.get("sandbox_mode", defaults.get("sandbox_mode"))
    operator_message = read_message(args)
    prompt_text = build_prompt(
        role_name=role_name,
        role_prompt_path=prompt_path,
        role_prompt_text=prompt_path.read_text(encoding="utf-8"),
        runtime_profile_name=profile_name or "<none>",
        runtime_profile=profile_cfg,
        resolved_model_hint=model,
        workflow_path=workflow_path,
        profiles_path=profiles_path,
        workspace=workspace,
        shared_context=workflow.get("multiagent", {}).get("shared_context", {}).get("required_files", []),
        operator_message=operator_message,
    )

    codex_bin = find_codex(args.codex_bin)
    command: list[str] = [codex_bin]
    if args.use_exec:
        command.append("exec")
    command.extend(["-C", str(workspace)])
    if args.codex_profile:
        command.extend(["-p", args.codex_profile])
    if model:
        command.extend(["-m", model])
    if args.oss:
        command.append("--oss")
    if args.local_provider:
        command.extend(["--local-provider", args.local_provider])
    if approval_policy:
        command.extend(["-a", approval_policy])
    if sandbox_mode:
        command.extend(["-s", sandbox_mode])
    if args.search:
        command.append("--search")
    if args.full_auto:
        command.append("--full-auto")
    if args.no_alt_screen:
        command.append("--no-alt-screen")
    if reasoning_effort:
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
    for feature in args.enable:
        command.extend(["--enable", feature])
    for feature in args.disable:
        command.extend(["--disable", feature])
    for image in args.image:
        resolved_image = resolve_path(image, Path.cwd())
        command.extend(["-i", str(resolved_image)])
    for add_dir in args.add_dir:
        resolved_add_dir = resolve_path(add_dir, Path.cwd())
        command.extend(["--add-dir", str(resolved_add_dir)])
    if args.use_exec:
        if args.skip_git_repo_check:
            command.append("--skip-git-repo-check")
        if args.ephemeral:
            command.append("--ephemeral")
        if args.output_schema:
            command.extend(["--output-schema", str(resolve_path(args.output_schema, Path.cwd()))])
        if args.color:
            command.extend(["--color", args.color])
        if args.progress_cursor:
            command.append("--progress-cursor")
        if args.json:
            command.append("--json")
        if args.output_last_message:
            command.extend(["-o", str(resolve_path(args.output_last_message, Path.cwd()))])

    if args.dry_run or args.print_prompt:
        print(f"role: {role_name}")
        print(f"workspace: {workspace}")
        print(f"workflow_config: {workflow_path}")
        print(f"profile_catalog: {profiles_path}")
        print(f"prompt_file: {prompt_path}")
        print(f"runtime_profile: {profile_name or '<none>'}")
        print(f"resolved_model: {model}")
        print(f"reasoning_effort: {reasoning_effort}")
        print(f"launch_mode: {'exec' if args.use_exec else 'interactive'}")
        print(f"command: {subprocess.list2cmdline(command + ['<PROMPT>'])}")
        print(f"prompt_lines: {len(prompt_text.splitlines())}")
        if args.print_prompt:
            print("")
            print(prompt_text, end="")
        if args.dry_run:
            return 0

    command.append(prompt_text)
    completed = subprocess.run(command, cwd=workspace)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
