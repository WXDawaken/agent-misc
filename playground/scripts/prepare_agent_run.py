from __future__ import annotations

import argparse
import json
from pathlib import Path

from runner_common import prepare_prompt_run, prepare_track_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an Arcane Lab agent runner workspace.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    track = subparsers.add_parser("track", help="Prepare a server-token track run.")
    track.add_argument("--runner", required=True)
    track.add_argument("--runner-client", required=True)
    track.add_argument("--model", required=True)
    track.add_argument("--reasoning-variant", required=True)
    track.add_argument("--track", required=True)
    track.add_argument("--track-config-path", default="envs/arcane_lab/docs/tracks/config.json")
    track.add_argument("--shared-prompt-path", default="")
    track.add_argument("--prompt-path", default="")
    track.add_argument("--out-dir", required=True)
    track.add_argument("--tick-budget", type=int)
    track.add_argument("--server-url", default="http://127.0.0.1:8765")
    track.add_argument("--label-prefix", required=True)
    track.add_argument("--report-name-template", required=True)
    track.add_argument(
        "--offline-practice",
        choices=("auto", "true", "false"),
        default="auto",
        help="Override track config offline_practice. auto uses the selected track config.",
    )

    prompt = subparsers.add_parser("prompt", help="Prepare a prompt-only runner workspace.")
    prompt.add_argument("--runner", required=True)
    prompt.add_argument("--model", required=True)
    prompt.add_argument("--effort", required=True)
    prompt.add_argument("--prompt-path", required=True)
    prompt.add_argument("--out-dir", required=True)
    prompt.add_argument("--workspace-profile", required=True)

    args = parser.parse_args()
    source_root = Path.cwd().resolve()
    if args.mode == "track":
        offline_override = None
        if args.offline_practice != "auto":
            offline_override = args.offline_practice == "true"
        result = prepare_track_run(
            source_root=source_root,
            runner=args.runner,
            runner_client=args.runner_client,
            model=args.model,
            reasoning_variant=args.reasoning_variant,
            track=args.track,
            track_config_path=args.track_config_path,
            shared_prompt_path=args.shared_prompt_path,
            prompt_path=args.prompt_path,
            out_dir=args.out_dir,
            tick_budget=args.tick_budget,
            server_url=args.server_url,
            label_prefix=args.label_prefix,
            report_name_template=args.report_name_template,
            offline_practice=offline_override,
        )
    else:
        result = prepare_prompt_run(
            source_root=source_root,
            runner=args.runner,
            model=args.model,
            effort=args.effort,
            prompt_path=args.prompt_path,
            out_dir=args.out_dir,
            workspace_profile=args.workspace_profile,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
