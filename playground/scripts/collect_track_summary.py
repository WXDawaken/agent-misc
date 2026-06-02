from __future__ import annotations

import argparse
import json
from pathlib import Path

import runner_common as common


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a completed Arcane Lab track run summary.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", default="")
    parser.add_argument("--stopped-reason", default="")
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--summary-out", default="")
    args = parser.parse_args()

    metadata_path = Path(args.metadata).resolve()
    metadata = common.load_json(metadata_path)
    runner_dir = Path(metadata.get("runner_dir") or metadata_path.parent)
    summary_path = Path(args.summary_out).resolve() if args.summary_out else runner_dir / "summary.json"
    report_path = Path(args.report).resolve() if args.report else None
    summary = common.build_track_summary(
        source_root=Path(args.source_root).resolve(),
        metadata_path=metadata_path,
        output_path=Path(args.output).resolve(),
        report_path=report_path,
        stopped_reason=args.stopped_reason or None,
        exit_code=args.exit_code,
    )
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
