from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import (
    PromptKitError,
    compile_prompt_document,
    lint_prompt_document,
    load_prompt_document,
    load_vars_file,
    render_prompt_document,
    snapshot_prompt_document,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render, lint, and snapshot prompt artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="Render a prompt to stdout or a file.")
    _add_common_prompt_args(render_parser)
    render_parser.add_argument("--out", type=Path, help="Optional rendered prompt output path.")
    render_parser.add_argument("--no-strict", action="store_true", help="Allow missing variables.")

    lint_parser = subparsers.add_parser("lint", help="Validate prompt metadata and variables.")
    _add_common_prompt_args(lint_parser)
    lint_parser.add_argument("--no-render", action="store_true", help="Skip strict render validation.")

    snapshot_parser = subparsers.add_parser("snapshot", help="Render and write a reproducible snapshot.")
    _add_common_prompt_args(snapshot_parser)
    snapshot_parser.add_argument("--out-dir", type=Path, default=Path(".prompt_snapshots"))
    snapshot_parser.add_argument("--no-strict", action="store_true", help="Allow missing variables.")

    compile_parser = subparsers.add_parser("compile", help="Compile a prompt artifact to JSON IR.")
    _add_common_prompt_args(compile_parser)
    compile_parser.add_argument("--out", type=Path, help="Optional JSON IR output path.")
    compile_parser.add_argument(
        "--no-partials",
        action="store_true",
        help="Do not resolve and embed partial definitions in the JSON IR.",
    )

    args = parser.parse_args(argv)
    try:
        variables = _load_variables(args)
        document = load_prompt_document(args.prompt)
        if args.command == "render":
            rendered, warnings = render_prompt_document(
                document,
                variables,
                strict=not args.no_strict,
                variant=args.variant,
            )
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(rendered, encoding="utf-8")
            else:
                sys.stdout.write(rendered)
            for warning in warnings:
                print(f"warning: {warning}", file=sys.stderr)
            return 0
        if args.command == "lint":
            messages = lint_prompt_document(document, variables, render=not args.no_render, variant=args.variant)
            for message in messages:
                print(f"{message.level}: {message.message}")
            return 1 if any(message.level == "error" for message in messages) else 0
        if args.command == "snapshot":
            snapshot_dir = snapshot_prompt_document(
                document,
                variables,
                args.out_dir,
                strict=not args.no_strict,
                variant=args.variant,
            )
            print(snapshot_dir)
            return 0
        if args.command == "compile":
            ir = compile_prompt_document(document, include_partials=not args.no_partials)
            text = json.dumps(ir, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(text, encoding="utf-8")
            else:
                sys.stdout.write(text)
            return 0
    except PromptKitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _add_common_prompt_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prompt", type=Path, help="Prompt artifact path.")
    parser.add_argument("--vars", type=Path, help="JSON or TOML variables file.")
    parser.add_argument("--variant", help="Named prompt variant to render or lint.")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Inline variable override. VALUE is parsed as JSON when possible.",
    )


def _load_variables(args: argparse.Namespace) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    if args.vars:
        variables.update(load_vars_file(args.vars))
    for assignment in args.var:
        key, value = _parse_assignment(assignment)
        _set_dotted(variables, key, value)
    return variables


def _parse_assignment(assignment: str) -> tuple[str, Any]:
    if "=" not in assignment:
        raise PromptKitError(f"Expected KEY=VALUE for --var, got `{assignment}`.")
    key, raw_value = assignment.split("=", 1)
    key = key.strip()
    if not key:
        raise PromptKitError("Inline variable key cannot be empty.")
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value
    return key, value


def _set_dotted(target: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    current = target
    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            existing = {}
            current[part] = existing
        if not isinstance(existing, dict):
            raise PromptKitError(f"Cannot assign nested key `{key}` because `{part}` is not an object.")
        current = existing
    current[parts[-1]] = value


if __name__ == "__main__":
    raise SystemExit(main())
