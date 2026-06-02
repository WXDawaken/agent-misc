from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAGE_TITLE = "Playground Test Results"

ENVIRONMENTS = {
    "arcane_lab": {
        "name": "Arcane Lab",
        "tagline": "Incremental text RPG for route planning, prestige timing, and official-run discipline.",
        "config": Path("envs/arcane_lab/docs/tracks/config.json"),
        "progress": Path("envs/arcane_lab/docs/progress.md"),
        "accent": "#2b6f8f",
        "notes": [
            "Budgeted prestige remains the main discriminator for long-route planning and official submission discipline.",
            "Strong GPT-series and OpenCode OpenAI samples solve consistently; DeepSeek improves when the harness constrains closure.",
            "Source-policy and helper discipline are tracked separately from route success.",
        ],
    },
    "ledger_tower": {
        "name": "Ledger Tower",
        "tagline": "Deterministic fixed-value tower puzzle RPG for exact move, HP, key, gold, and route-score accounting.",
        "config": Path("envs/ledger_tower/docs/tracks/config.json"),
        "progress": Path("envs/ledger_tower/docs/progress.md"),
        "accent": "#6f7f2b",
        "notes": [
            "Core fixed-map lanes separate token-limited, practice-budgeted, and best-of-N official scoring.",
            "Boss-gated and generated 8-floor variants are separated from core to keep topology changes explicit.",
            "Recent runs show official helper ergonomics matter, but route hygiene and source-policy compliance remain distinct axes.",
        ],
    },
}


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def rel(path_value: Any, base: Path) -> str | None:
    if not path_value:
        return None
    try:
        path = Path(str(path_value))
    except TypeError:
        return None
    if not path.is_absolute():
        return str(path_value).replace("\\", "/")
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def num(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def short_hash(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:12]


def date_from_text(*values: Any) -> str | None:
    joined = " ".join(str(v) for v in values if v)
    match = re.search(r"(20\d{6})[_-](\d{6})", joined)
    if not match:
        match = re.search(r"(20\d{6})", joined)
    if not match:
        return None
    raw = match.group(1)
    try:
        return datetime.strptime(raw, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def load_env_track_index(playground_root: Path) -> tuple[dict[str, str], dict[str, dict[str, Any]], dict[str, Any]]:
    track_to_env: dict[str, str] = {}
    track_meta: dict[str, dict[str, Any]] = {}
    env_payload: dict[str, Any] = {}
    for env_id, env in ENVIRONMENTS.items():
        config_path = playground_root / env["config"]
        config = load_json(config_path) or {}
        suites = config.get("suites") if isinstance(config.get("suites"), dict) else {}
        tracks = config.get("tracks") if isinstance(config.get("tracks"), dict) else {}
        suite_for_track: dict[str, list[str]] = defaultdict(list)
        for suite_name, suite in suites.items():
            for track in suite.get("tracks", []) if isinstance(suite, dict) else []:
                suite_for_track[str(track)].append(str(suite_name))
        env_payload[env_id] = {
            "id": env_id,
            "name": env["name"],
            "tagline": env["tagline"],
            "accent": env["accent"],
            "progressPath": env["progress"].as_posix(),
            "trackCount": len(tracks),
            "suites": {
                name: {
                    "description": suite.get("description", "") if isinstance(suite, dict) else "",
                    "tracks": suite.get("tracks", []) if isinstance(suite, dict) else [],
                }
                for name, suite in suites.items()
            },
            "notes": env["notes"],
        }
        for track, info in tracks.items():
            track = str(track)
            track_to_env[track] = env_id
            track_meta[track] = {
                "env": env_id,
                "track": track,
                "suites": suite_for_track.get(track, []),
                "offlinePractice": info.get("offline_practice") if isinstance(info, dict) else None,
                "practiceMode": (
                    info.get("practice", {}).get("mode")
                    if isinstance(info, dict) and isinstance(info.get("practice"), dict)
                    else None
                ),
                "officialAttempts": info.get("official_attempts") if isinstance(info, dict) else None,
                "officialScoring": info.get("official_scoring") if isinstance(info, dict) else None,
                "tickBudget": info.get("tick_budget") if isinstance(info, dict) else None,
                "softStop": False if isinstance(info, dict) and info.get("soft_stop") is False else None,
                "softStopGap": info.get("soft_stop_gap") if isinstance(info, dict) else None,
                "dataPath": info.get("data_path") if isinstance(info, dict) else None,
            }
    return track_to_env, track_meta, env_payload


def candidate_json_paths(playground_root: Path) -> list[Path]:
    roots = [playground_root / "agent_workspaces", playground_root / "logs"]
    paths: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        paths.update(root.rglob(".runner/summary.json"))
        paths.update(root.rglob("*_matrix_*.json"))
        paths.update(root.rglob("warmup_matrix.json"))
    return sorted(paths)


def rows_from_json(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, dict):
        rows = [payload]
    elif isinstance(payload, list):
        rows = [row for row in payload if isinstance(row, dict)]
    else:
        rows = []
    return [row for row in rows if row.get("runner") and row.get("model") and row.get("track")]


def load_metadata_for_row(row: dict[str, Any], source_path: Path) -> dict[str, Any]:
    candidates: list[Path] = []
    if source_path.name == "summary.json" and source_path.parent.name == ".runner":
        candidates.append(source_path.parent / "metadata.json")
    run_dir = row.get("run_dir") or row.get("workspace")
    if run_dir:
        candidates.append(Path(str(run_dir)) / ".runner" / "metadata.json")
    for path in candidates:
        metadata = load_json(path)
        if isinstance(metadata, dict):
            return metadata
    return {}


def infer_env(row: dict[str, Any], metadata: dict[str, Any], track_to_env: dict[str, str]) -> str | None:
    for source in (row, metadata):
        env_id = source.get("env_id")
        if isinstance(env_id, str) and env_id in ENVIRONMENTS:
            return env_id
        environment_root = str(source.get("environment_root") or "").replace("\\", "/")
        for env_id in ENVIRONMENTS:
            if f"envs/{env_id}" in environment_root:
                return env_id
    track = str(row.get("track") or "")
    return track_to_env.get(track)


def status_for(row: dict[str, Any]) -> str:
    if row.get("reward") is None and not row.get("verification_path"):
        return "no-score"
    if row.get("goal_achieved") is True or row.get("outcome") == "success":
        return "success"
    if row.get("outcome") == "partial":
        return "partial"
    if row.get("accepted") is False:
        return "rejected"
    if row.get("accepted") is True:
        return "accepted"
    return "unknown"


def clean_violation_names(source_policy: Any) -> list[str]:
    if not isinstance(source_policy, dict):
        return []
    out: list[str] = []
    for violation in source_policy.get("violations", []) or []:
        if not isinstance(violation, dict):
            continue
        name = violation.get("name") or violation.get("pattern")
        if isinstance(name, str) and name and name not in out:
            out.append(name[:80])
    return out[:6]


def sanitize_row(
    row: dict[str, Any],
    metadata: dict[str, Any],
    source_path: Path,
    playground_root: Path,
    track_meta: dict[str, dict[str, Any]],
    env_id: str,
) -> dict[str, Any]:
    route_quality = row.get("route_quality") if isinstance(row.get("route_quality"), dict) else {}
    signals = route_quality.get("signals") if isinstance(route_quality.get("signals"), dict) else {}
    source_policy = row.get("source_policy") if isinstance(row.get("source_policy"), dict) else {}
    track = str(row.get("track"))
    meta = track_meta.get(track, {})
    date = (
        date_from_text(metadata.get("timestamp"))
        or date_from_text(row.get("task_id"), row.get("run_dir"), row.get("game_id"), source_path)
    )
    moves = num(row.get("moves"))
    lifetime_tick = num(row.get("lifetime_tick"))
    tick = num(row.get("tick"))
    budget = (
        num(metadata.get("token_lifetime_tick_budget"))
        or num(metadata.get("token_tick_budget"))
        or num(signals.get("tick_budget"))
    )
    soft_stop = num(metadata.get("token_soft_stop_tick")) or num(row.get("soft_stop_tick")) or num(signals.get("soft_stop_tick"))
    failed_commands = num(signals.get("failed_command_count"))
    violation_count = num(source_policy.get("violation_count")) or 0
    usage = row.get("usage") if isinstance(row.get("usage"), dict) else {}
    transcript_stats = row.get("transcript_stats") if isinstance(row.get("transcript_stats"), dict) else {}
    cost = num(transcript_stats.get("cost_usd")) or num(row.get("cost_usd"))
    status = status_for(row)
    relative_run = rel(row.get("run_dir") or row.get("workspace"), playground_root)
    relative_source = rel(source_path, playground_root)
    row_id = str(row.get("task_id") or relative_run or f"{relative_source}:{track}")
    data_path = metadata.get("data_path") or meta.get("dataPath")
    return {
        "id": row_id,
        "env": env_id,
        "date": date,
        "runner": row.get("runner"),
        "model": row.get("model"),
        "reasoning": row.get("reasoning_variant") or row.get("reasoning_effort") or row.get("effort"),
        "track": track,
        "suites": meta.get("suites", []),
        "status": status,
        "outcome": row.get("outcome"),
        "accepted": row.get("accepted"),
        "goalAchieved": row.get("goal_achieved"),
        "reward": num(row.get("reward")),
        "qualityScore": num(route_quality.get("score")),
        "qualityGrade": route_quality.get("grade"),
        "moves": moves,
        "lifetimeTick": lifetime_tick,
        "tick": tick,
        "budget": budget,
        "budgetUsed": moves if moves is not None else lifetime_tick if lifetime_tick is not None else tick,
        "softStop": soft_stop,
        "softStopExceeded": row.get("soft_stop_exceeded"),
        "sourceViolations": violation_count,
        "sourceViolationNames": clean_violation_names(source_policy),
        "failedCommands": failed_commands,
        "retirements": num(row.get("retirements")) or num(signals.get("retirements")),
        "gameId": row.get("game_id"),
        "trajectory": short_hash(row.get("trajectory_hash")),
        "wallClockSec": num(row.get("wall_clock_sec")),
        "eventCount": num(row.get("event_count")),
        "inputTokens": num(usage.get("input_tokens")),
        "outputTokens": num(usage.get("output_tokens")),
        "costUsd": cost,
        "practiceMode": metadata.get("practice_mode") or meta.get("practiceMode"),
        "workspaceMode": metadata.get("workspace_mode"),
        "officialAttempts": metadata.get("official_attempts") or meta.get("officialAttempts"),
        "officialScoring": metadata.get("official_scoring_policy") or meta.get("officialScoring"),
        "dataPath": rel(data_path, playground_root),
        "warnings": route_quality.get("warnings", [])[:4] if isinstance(route_quality.get("warnings"), list) else [],
        "paths": {
            "source": relative_source,
            "run": relative_run,
            "report": rel(row.get("report"), playground_root),
            "verification": rel(row.get("verification_path"), playground_root),
        },
    }


def row_quality_score(row: dict[str, Any]) -> int:
    fields = ["verification_path", "reward", "route_quality", "source_policy", "game_id", "wall_clock_sec"]
    return sum(1 for field in fields if row.get(field) is not None)


def collect_runs(playground_root: Path, track_to_env: dict[str, str], track_meta: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for source_path in candidate_json_paths(playground_root):
        for raw in rows_from_json(source_path):
            metadata = load_metadata_for_row(raw, source_path)
            env_id = infer_env(raw, metadata, track_to_env)
            if not env_id:
                continue
            clean = sanitize_row(raw, metadata, source_path, playground_root, track_meta, env_id)
            key = clean["id"]
            score = row_quality_score(raw)
            if key not in by_id or score > by_id[key][0]:
                by_id[key] = (score, clean)
    runs = [row for _, row in by_id.values()]
    runs.sort(key=lambda row: (row.get("date") or "", row.get("runner") or "", row.get("model") or "", row.get("track") or ""), reverse=True)
    return runs


def summarize(runs: list[dict[str, Any]], env_payload: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload: dict[str, Any] = {
        "title": PAGE_TITLE,
        "generatedAt": now,
        "environments": env_payload,
        "runs": runs,
        "summary": {},
        "trackStats": {},
    }
    status_counts = Counter(row["status"] for row in runs)
    payload["summary"] = {
        "runCount": len(runs),
        "envCount": len({row["env"] for row in runs}),
        "successCount": status_counts.get("success", 0),
        "partialCount": status_counts.get("partial", 0),
        "noScoreCount": status_counts.get("no-score", 0),
        "sourceCleanCount": sum(1 for row in runs if row.get("sourceViolations", 0) == 0),
        "latestDate": max((row["date"] for row in runs if row.get("date")), default=None),
    }
    by_env_track: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in runs:
        by_env_track[row["env"]][row["track"]].append(row)
    for env_id, tracks in by_env_track.items():
        payload["trackStats"][env_id] = {}
        for track, rows in sorted(tracks.items()):
            successes = [row for row in rows if row["status"] == "success"]
            scored = [row for row in rows if row.get("reward") is not None]
            best_reward = max((row["reward"] for row in scored if row.get("reward") is not None), default=None)
            best_quality = max((row["qualityScore"] for row in rows if row.get("qualityScore") is not None), default=None)
            best = sorted(
                scored,
                key=lambda row: (
                    row.get("reward") if row.get("reward") is not None else -1,
                    row.get("qualityScore") if row.get("qualityScore") is not None else -1,
                ),
                reverse=True,
            )
            payload["trackStats"][env_id][track] = {
                "track": track,
                "runs": len(rows),
                "successes": len(successes),
                "partials": sum(1 for row in rows if row["status"] == "partial"),
                "noScores": sum(1 for row in rows if row["status"] == "no-score"),
                "sourceClean": sum(1 for row in rows if row.get("sourceViolations", 0) == 0),
                "bestReward": best_reward,
                "bestQuality": best_quality,
                "bestModel": f"{best[0]['runner']} / {best[0]['model']}" if best else None,
                "suites": rows[0].get("suites", []),
            }
    return payload


def render_index() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(PAGE_TITLE)}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">Playground benchmark archive</p>
      <h1>Test Results By Environment</h1>
    </div>
    <div class="generated" id="generatedAt"></div>
  </header>

  <main>
    <section class="summary-band" id="summaryBand" aria-label="Summary"></section>

    <section class="interpretation-note" aria-label="Metric interpretation note">
      <strong>Reward and quality are separate signals.</strong>
      Reward is the environment score; quality is an independent review/rubric signal, so a higher reward does not automatically imply a higher quality grade.
    </section>

    <section class="controls" aria-label="Filters">
      <label>
        <span>Environment</span>
        <select id="envFilter"></select>
      </label>
      <label>
        <span>Runner</span>
        <select id="runnerFilter"></select>
      </label>
      <label>
        <span>Status</span>
        <select id="statusFilter">
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="partial">Partial</option>
          <option value="no-score">No score</option>
          <option value="accepted">Accepted</option>
          <option value="rejected">Rejected</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>
      <label>
        <span>Search</span>
        <input id="searchFilter" type="search" placeholder="model, track, game id">
      </label>
      <label class="check">
        <input id="cleanOnly" type="checkbox">
        <span>Source clean only</span>
      </label>
    </section>

    <div id="envSections"></div>
  </main>

  <script src="data.js"></script>
  <script src="app.js"></script>
</body>
</html>
"""


def render_css() -> str:
    return """* {
  box-sizing: border-box;
}

:root {
  color-scheme: light;
  --bg: #f6f7f4;
  --ink: #18202a;
  --muted: #657181;
  --line: #d9ded8;
  --panel: #ffffff;
  --panel-2: #eef2f0;
  --blue: #2b6f8f;
  --green: #3f7b52;
  --gold: #9a721e;
  --red: #a54848;
  --violet: #6b5e9b;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
  line-height: 1.45;
}

.topbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  padding: 24px clamp(18px, 4vw, 48px) 16px;
  border-bottom: 1px solid var(--line);
  background: #fbfcfa;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0;
}

h1, h2, h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 28px;
  line-height: 1.1;
}

h2 {
  font-size: 22px;
}

h3 {
  font-size: 15px;
}

main {
  padding: 18px clamp(18px, 4vw, 48px) 40px;
}

.generated {
  color: var(--muted);
  font-size: 12px;
  text-align: right;
}

.summary-band {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.metric {
  min-height: 76px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel);
}

.metric .label {
  color: var(--muted);
  font-size: 12px;
}

.metric .value {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 700;
}

.metric .sub {
  color: var(--muted);
  font-size: 12px;
}

.interpretation-note {
  margin: -4px 0 16px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-left: 4px solid var(--blue);
  border-radius: 6px;
  background: #fbfcfa;
  color: var(--muted);
}

.interpretation-note strong {
  color: var(--ink);
}

.controls {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 2fr auto;
  gap: 10px;
  align-items: end;
  margin-bottom: 20px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel-2);
}

label {
  display: grid;
  gap: 4px;
  color: var(--muted);
  font-size: 12px;
}

select,
input[type="search"] {
  width: 100%;
  min-height: 34px;
  border: 1px solid #c8d0cc;
  border-radius: 4px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  padding: 6px 8px;
}

.check {
  grid-template-columns: auto 1fr;
  align-items: center;
  min-height: 34px;
  padding: 7px 8px;
  border: 1px solid #c8d0cc;
  border-radius: 4px;
  background: #fff;
  color: var(--ink);
}

.env-section {
  margin-top: 22px;
  border-top: 4px solid var(--env-accent, var(--blue));
  background: transparent;
}

.env-heading {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
  padding: 16px 0 10px;
}

.env-heading p {
  max-width: 820px;
  margin: 6px 0 0;
  color: var(--muted);
}

.env-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(90px, 1fr));
  gap: 8px;
  min-width: 360px;
}

.small-stat {
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel);
}

.small-stat strong {
  display: block;
  font-size: 18px;
}

.notes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.note {
  min-height: 56px;
  padding: 10px;
  border-left: 3px solid var(--env-accent, var(--blue));
  background: #fff;
  color: #3d4650;
}

.tables {
  display: grid;
  gap: 14px;
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel);
}

.table-details {
  overflow: visible;
}

.table-details > summary {
  cursor: pointer;
}

.details-table-scroll {
  overflow: auto;
}

.table-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  background: #fbfcfa;
}

.table-title span {
  color: var(--muted);
  font-size: 12px;
}

.title-main {
  display: grid;
  gap: 2px;
}

.segmented {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid #c8d0cc;
  border-radius: 6px;
  background: #fff;
}

.segmented button {
  min-height: 30px;
  border: 0;
  border-right: 1px solid #c8d0cc;
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  padding: 5px 10px;
  cursor: pointer;
}

.segmented button:last-child {
  border-right: 0;
}

.segmented button.active {
  background: var(--blue);
  color: #fff;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 860px;
}

th,
td {
  padding: 9px 10px;
  border-bottom: 1px solid #edf0ec;
  text-align: left;
  vertical-align: middle;
}

th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f3f6f4;
  color: #45505d;
  font-size: 12px;
  font-weight: 650;
}

tbody tr:hover {
  background: #f8faf8;
}

.track-name {
  font-weight: 650;
}

.heatmap-wrap {
  overflow: auto;
}

.heatmap-table {
  width: max-content;
  min-width: 100%;
  table-layout: fixed;
}

.heatmap-table th,
.heatmap-table td {
  padding: 4px;
}

.heat-track {
  position: sticky;
  left: 0;
  z-index: 2;
  width: 150px;
  max-width: 150px;
  background: #f3f6f4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.heatmap-table thead .heat-track {
  z-index: 3;
}

.heat-col {
  width: 74px;
  max-width: 74px;
  white-space: nowrap;
}

.heat-col div {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 11px;
  font-weight: 750;
}

.heat-col span {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 10px;
  font-weight: 500;
}

.heatmap-cell {
  height: 38px;
  border: 1px solid #fff;
  border-radius: 4px;
  text-align: center;
  vertical-align: middle;
}

.heatmap-cell .heat-value {
  font-size: 11px;
  font-weight: 750;
}

.heatmap-cell .heat-sub {
  margin-top: 1px;
  font-size: 10px;
}

.heat-empty {
  background: #f1f3f1;
  color: #97a19b;
}

.heat-success {
  background: #d8eddf;
  color: #215d36;
}

.heat-partial {
  background: #f8e9bd;
  color: #75520f;
}

.heat-rejected {
  background: #efd1d1;
  color: #833030;
}

.heat-noscore,
.heat-unknown {
  background: #e5ebef;
  color: #52606d;
}

.track-list {
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
}

.harness-row td {
  border-bottom: 0;
}

.group-details-row td {
  padding: 0 10px 10px;
  background: #fbfcfa;
  border-bottom: 1px solid #e1e7e2;
}

.group-details-row:hover {
  background: transparent;
}

.run-details summary {
  cursor: pointer;
  color: var(--blue);
  font-weight: 650;
  padding: 7px 9px;
  white-space: nowrap;
}

.run-details {
  border: 1px solid #e2e8e4;
  border-radius: 5px;
  background: #fff;
}

.run-detail-panel {
  max-height: 280px;
  overflow: auto;
  border-top: 1px solid #edf0ec;
  background: #fff;
}

.run-detail-table {
  min-width: 760px;
  font-size: 12px;
}

.run-detail-table th,
.run-detail-table td {
  padding: 5px 6px;
  border-bottom: 1px solid #edf0ec;
  white-space: nowrap;
}

.run-detail-table th {
  position: static;
  z-index: auto;
  background: #f8faf8;
  font-size: 12px;
}

.run-detail-table .run-track {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.run-detail-table .pill {
  min-height: 18px;
  padding: 1px 5px;
  font-size: 11px;
}

.muted {
  color: var(--muted);
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 22px;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}

.status-success {
  background: #e4f2e8;
  color: #23633b;
}

.status-partial,
.status-accepted {
  background: #fff0cf;
  color: #7a5511;
}

.status-no-score,
.status-unknown {
  background: #e9edf1;
  color: #54606d;
}

.status-rejected {
  background: #f5dfdf;
  color: #8f3333;
}

.quality {
  display: grid;
  grid-template-columns: 28px minmax(80px, 1fr);
  gap: 8px;
  align-items: center;
}

.grade {
  font-weight: 750;
}

.bar {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e3e7e4;
}

.bar > span {
  display: block;
  height: 100%;
  width: var(--w, 0%);
  border-radius: inherit;
  background: linear-gradient(90deg, var(--blue), var(--green));
}

.source-bad {
  color: var(--red);
  font-weight: 700;
}

.source-clean {
  color: var(--green);
  font-weight: 700;
}

.empty {
  padding: 28px;
  border: 1px dashed var(--line);
  border-radius: 6px;
  color: var(--muted);
  background: #fff;
}

@media (max-width: 980px) {
  .summary-band {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }

  .controls {
    grid-template-columns: 1fr 1fr;
  }

  .env-heading {
    grid-template-columns: 1fr;
  }

  .env-stats {
    min-width: 0;
  }

  .notes {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .topbar {
    display: grid;
    align-items: start;
  }

  .generated {
    text-align: left;
  }

  .summary-band,
  .controls,
  .env-stats {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 24px;
  }
}
"""


def render_js() -> str:
    return """const data = window.PLAYGROUND_RESULTS;

const state = {
  env: "",
  runner: "",
  status: "",
  search: "",
  cleanOnly: false,
  trackView: "table",
};

const fmt = new Intl.NumberFormat("en-US");
const pct = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function number(value) {
  return value === null || value === undefined ? "" : fmt.format(value);
}

function seconds(value) {
  if (value === null || value === undefined) return "";
  if (value < 60) return `${Math.round(value)}s`;
  return `${pct.format(value / 60)}m`;
}

function quality(row) {
  if (row.qualityScore === null || row.qualityScore === undefined) return '<span class="muted">-</span>';
  const width = Math.max(0, Math.min(100, row.qualityScore * 100));
  return `<div class="quality"><span class="grade">${esc(row.qualityGrade || "")}</span><span class="bar" title="${pct.format(width)}%"><span style="--w:${width}%"></span></span></div>`;
}

function statusPill(status) {
  const label = {
    "success": "Success",
    "partial": "Partial",
    "no-score": "No score",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "unknown": "Unknown",
  }[status] || status;
  return `<span class="pill status-${esc(status)}">${esc(label)}</span>`;
}

function sourceCell(row) {
  const count = row.sourceViolations || 0;
  if (!count) return '<span class="source-clean">clean</span>';
  const title = (row.sourceViolationNames || []).join(", ");
  return `<span class="source-bad" title="${esc(title)}">${count} hit${count === 1 ? "" : "s"}</span>`;
}

function budgetCell(row) {
  const used = row.budgetUsed;
  const budget = row.budget;
  if (used === null || used === undefined) return '<span class="muted">-</span>';
  const suffix = budget ? ` / ${number(budget)}` : "";
  return `<span>${number(used)}${suffix}</span>`;
}

function filteredRuns() {
  const q = state.search.trim().toLowerCase();
  return data.runs.filter(row => {
    if (state.env && row.env !== state.env) return false;
    if (state.runner && row.runner !== state.runner) return false;
    if (state.status && row.status !== state.status) return false;
    if (state.cleanOnly && (row.sourceViolations || 0) > 0) return false;
    if (q) {
      const hay = [
        row.model,
        row.runner,
        row.track,
        row.gameId,
        row.status,
        row.reasoning,
      ].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function envStats(rows) {
  const success = rows.filter(row => row.status === "success").length;
  const scored = rows.filter(row => row.reward !== null && row.reward !== undefined).length;
  const clean = rows.filter(row => !row.sourceViolations).length;
  const bestReward = rows.reduce((best, row) => row.reward !== null && row.reward !== undefined ? Math.max(best, row.reward) : best, 0);
  return { runs: rows.length, success, scored, clean, bestReward };
}

function populateControls() {
  const envSelect = document.querySelector("#envFilter");
  envSelect.innerHTML = '<option value="">All environments</option>' + Object.values(data.environments)
    .map(env => `<option value="${esc(env.id)}">${esc(env.name)}</option>`)
    .join("");

  const runnerSelect = document.querySelector("#runnerFilter");
  const runners = Array.from(new Set(data.runs.map(row => row.runner).filter(Boolean))).sort();
  runnerSelect.innerHTML = '<option value="">All runners</option>' + runners
    .map(runner => `<option value="${esc(runner)}">${esc(runner)}</option>`)
    .join("");

  envSelect.addEventListener("change", event => {
    state.env = event.target.value;
    render();
  });
  runnerSelect.addEventListener("change", event => {
    state.runner = event.target.value;
    render();
  });
  document.querySelector("#statusFilter").addEventListener("change", event => {
    state.status = event.target.value;
    render();
  });
  document.querySelector("#searchFilter").addEventListener("input", event => {
    state.search = event.target.value;
    render();
  });
  document.querySelector("#cleanOnly").addEventListener("change", event => {
    state.cleanOnly = event.target.checked;
    render();
  });
  document.querySelector("#envSections").addEventListener("click", event => {
    const button = event.target.closest?.("[data-track-view]");
    if (!button) return;
    state.trackView = button.dataset.trackView || "table";
    render();
  });
}

function renderSummary(rows) {
  const stats = envStats(rows);
  const successRate = stats.runs ? (stats.success / stats.runs) * 100 : 0;
  const cleanRate = stats.runs ? (stats.clean / stats.runs) * 100 : 0;
  document.querySelector("#summaryBand").innerHTML = [
    ["Runs", number(stats.runs), `${number(stats.scored)} scored`],
    ["Success", number(stats.success), `${pct.format(successRate)}%`],
    ["Source clean", number(stats.clean), `${pct.format(cleanRate)}%`],
    ["Best reward", number(stats.bestReward), "highest visible score"],
    ["Environments", number(new Set(rows.map(row => row.env)).size), `${data.summary.latestDate || ""}`],
    ["Generated", data.generatedAt.slice(0, 10), "UTC snapshot"],
  ].map(([label, value, sub]) => `<div class="metric"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><div class="sub">${esc(sub)}</div></div>`).join("");
  document.querySelector("#generatedAt").textContent = `Generated ${data.generatedAt}`;
}

function trackViewToggle() {
  const button = view => `<button type="button" class="${state.trackView === view ? "active" : ""}" data-track-view="${esc(view)}">${view === "table" ? "Table" : "Heatmap"}</button>`;
  return `<div class="segmented" aria-label="Track matrix view">${button("table")}${button("heatmap")}</div>`;
}

function trackMatrixTitle(trackCount) {
  return `<div class="table-title matrix-title">
    <div class="title-main"><h3>Track Matrix</h3><span>${number(trackCount)} tracks</span></div>
    ${trackViewToggle()}
  </div>`;
}

function statusWeight(status) {
  return {
    "success": 5,
    "accepted": 4,
    "partial": 3,
    "no-score": 2,
    "unknown": 1,
    "rejected": 0,
  }[status] ?? 1;
}

function bestRun(rows) {
  return rows.slice().sort((a, b) => {
    const reward = (b.reward ?? -1) - (a.reward ?? -1);
    if (reward) return reward;
    const qualityScore = (b.qualityScore ?? -1) - (a.qualityScore ?? -1);
    if (qualityScore) return qualityScore;
    const status = statusWeight(b.status) - statusWeight(a.status);
    if (status) return status;
    return String(b.date || "").localeCompare(String(a.date || ""));
  })[0];
}

function heatClass(row) {
  if (!row) return "heat-empty";
  if (row.status === "success") return "heat-success";
  if (row.status === "accepted" || row.status === "partial") return "heat-partial";
  if (row.status === "rejected") return "heat-rejected";
  if (row.status === "no-score") return "heat-noscore";
  return "heat-unknown";
}

function compactNumber(value) {
  if (value === null || value === undefined) return "-";
  const abs = Math.abs(value);
  if (abs >= 1000000) return `${pct.format(value / 1000000)}m`;
  if (abs >= 1000) return `${pct.format(value / 1000)}k`;
  return number(value);
}

function compactQuality(row) {
  if (row.qualityScore === null || row.qualityScore === undefined) return row.qualityGrade || "-";
  const grade = row.qualityGrade ? `${row.qualityGrade} ` : "";
  return `${grade}${Math.round(row.qualityScore * 100)}%`;
}

function compactRunner(value) {
  return String(value || "")
    .replace("claude-code-deepseek", "cc-ds")
    .replace("codex-cli", "codex")
    .replace("opencode", "open")
    .replace("reasonix", "rx");
}

function compactModel(value) {
  return String(value || "")
    .replace(/^opencode[/]/, "")
    .replace("deepseek-v4-", "ds-")
    .replace("claude-opus-", "opus-")
    .replace("gemini-", "gem-")
    .replace("minimax-", "mm-")
    .replace("[1m]", " 1m");
}

function compactReasoning(value) {
  const labels = { high: "h", low: "l", medium: "m", max: "max" };
  return labels[value] || value || "";
}

function heatCell(track, group) {
  const row = bestRun(group.rows.filter(item => item.track === track));
  if (!row) return '<td class="heatmap-cell heat-empty"><span>-</span></td>';
  const title = [
    track,
    `${group.runner} / ${group.model}${group.reasoning ? ` / ${group.reasoning}` : ""}`,
    row.status,
    `reward ${rewardLabel(row)}`,
    `quality ${qualityLabel(row)}`,
    row.date || "",
  ].filter(Boolean).join(" | ");
  return `<td class="heatmap-cell ${heatClass(row)}" title="${esc(title)}">
    <div class="heat-value">${esc(compactNumber(row.reward))}</div>
    <div class="heat-sub">${esc(compactQuality(row))}</div>
  </td>`;
}

function heatmapTable(rows) {
  const tracks = Array.from(new Set(rows.map(row => row.track).filter(Boolean))).sort();
  const groups = buildHarnessModelGroups(rows);
  const head = groups.map(group => {
    const full = `${group.runner} / ${group.model}${group.reasoning ? ` / ${group.reasoning}` : ""}`;
    const compact = `${compactModel(group.model)}${group.reasoning ? ` ${compactReasoning(group.reasoning)}` : ""}`;
    return `<th class="heat-col" title="${esc(full)}"><div>${esc(compactRunner(group.runner))}</div><span>${esc(compact)}</span></th>`;
  }).join("");
  const body = tracks.map(track => `<tr>
    <th class="heat-track">${esc(track)}</th>
    ${groups.map(group => heatCell(track, group)).join("")}
  </tr>`).join("");
  return `<div class="heatmap-wrap">
    <table class="heatmap-table">
      <thead><tr><th class="heat-track">Track</th>${head}</tr></thead>
      <tbody>${body}</tbody>
    </table>
  </div>`;
}

function trackTable(envId, rows) {
  const byTrack = new Map();
  for (const row of rows) {
    if (!byTrack.has(row.track)) byTrack.set(row.track, []);
    byTrack.get(row.track).push(row);
  }
  const html = Array.from(byTrack.entries()).sort((a, b) => a[0].localeCompare(b[0])).map(([track, trackRows]) => {
    const stats = envStats(trackRows);
    const successes = trackRows.filter(row => row.status === "success").length;
    const best = trackRows
      .filter(row => row.reward !== null && row.reward !== undefined)
      .sort((a, b) => (b.reward - a.reward) || ((b.qualityScore || 0) - (a.qualityScore || 0)))[0];
    const clean = trackRows.filter(row => !row.sourceViolations).length;
    const rate = trackRows.length ? (successes / trackRows.length) * 100 : 0;
    return `<tr>
      <td><div class="track-name">${esc(track)}</div><div class="muted">${esc((best?.suites || []).join(", "))}</div></td>
      <td>${number(trackRows.length)}</td>
      <td>${number(successes)} <span class="muted">(${pct.format(rate)}%)</span></td>
      <td>${number(stats.scored)}</td>
      <td>${number(clean)}</td>
      <td>${best ? number(best.reward) : '<span class="muted">-</span>'}</td>
      <td>${best ? quality(best) : '<span class="muted">-</span>'}</td>
      <td>${best ? `${esc(best.runner)} / ${esc(best.model)}` : '<span class="muted">-</span>'}</td>
    </tr>`;
  }).join("");
  const table = `<table>
      <thead><tr><th>Track</th><th>Runs</th><th>Success</th><th>Scored</th><th>Source Clean</th><th>Best Reward</th><th>Best Quality</th><th>Best Scored Sample</th></tr></thead>
      <tbody>${html}</tbody>
    </table>`;
  return `<div class="table-wrap">
    ${trackMatrixTitle(byTrack.size)}
    ${state.trackView === "heatmap" ? heatmapTable(rows) : table}
  </div>`;
}

function bestScoredRun(rows) {
  return rows
    .filter(row => row.reward !== null && row.reward !== undefined)
    .sort((a, b) => (b.reward - a.reward) || ((b.qualityScore || 0) - (a.qualityScore || 0)))[0];
}

function trackList(rows) {
  const tracks = Array.from(new Set(rows.map(row => row.track).filter(Boolean))).sort();
  const visible = tracks.slice(0, 2).map(track => esc(track)).join(", ");
  const suffix = tracks.length > 2 ? ` <span class="muted">+${number(tracks.length - 2)} tracks</span>` : "";
  return `<div class="track-list" title="${esc(tracks.join(", "))}">${visible}${suffix}</div>`;
}

function sortedRuns(rows) {
  return rows.slice().sort((a, b) => {
    const date = String(b.date || "").localeCompare(String(a.date || ""));
    if (date) return date;
    const reward = (b.reward ?? -1) - (a.reward ?? -1);
    if (reward) return reward;
    return String(a.track).localeCompare(String(b.track));
  });
}

function rewardLabel(row) {
  return row.reward === null || row.reward === undefined ? "-" : number(row.reward);
}

function qualityLabel(row) {
  if (row.qualityScore === null || row.qualityScore === undefined) return "-";
  const grade = row.qualityGrade ? `${row.qualityGrade} ` : "";
  return `${grade}${pct.format(row.qualityScore * 100)}%`;
}

function budgetLabel(row) {
  if (row.budgetUsed === null || row.budgetUsed === undefined) return "-";
  return `${number(row.budgetUsed)}${row.budget ? ` / ${number(row.budget)}` : ""}`;
}

function sourceLabel(row) {
  const count = row.sourceViolations || 0;
  return count ? `${count} hit${count === 1 ? "" : "s"}` : "clean";
}

function groupRunDetails(rows) {
  const trackCount = new Set(rows.map(row => row.track).filter(Boolean)).size;
  const trackWord = trackCount === 1 ? "track" : "tracks";
  const body = sortedRuns(rows).map(row => `<tr>
    <td>${esc(row.date || "")}</td>
    <td class="run-track" title="${esc(row.track)}">${esc(row.track)}</td>
    <td>${statusPill(row.status)}</td>
    <td>${esc(rewardLabel(row))}</td>
    <td>${esc(qualityLabel(row))}</td>
    <td>${esc(budgetLabel(row))}</td>
    <td>${esc(sourceLabel(row))}</td>
    <td>${esc(seconds(row.wallClockSec) || "-")}</td>
  </tr>`).join("");
  return `<details class="run-details">
    <summary>Run details - ${number(rows.length)} runs - ${number(trackCount)} ${trackWord}</summary>
    <div class="run-detail-panel">
      <table class="run-detail-table">
        <thead><tr><th>Date</th><th>Track</th><th>Status</th><th>Reward</th><th>Quality</th><th>Budget</th><th>Source</th><th>Wall</th></tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  </details>`;
}

function buildHarnessModelGroups(rows) {
  const byHarnessModel = new Map();
  for (const row of rows) {
    const key = [row.runner || "", row.model || "", row.reasoning || ""].join("\\u001f");
    if (!byHarnessModel.has(key)) byHarnessModel.set(key, []);
    byHarnessModel.get(key).push(row);
  }
  return Array.from(byHarnessModel.entries()).map(([key, groupRows]) => {
    const [runner, model, reasoning] = key.split("\\u001f");
    const stats = envStats(groupRows);
    const best = bestScoredRun(groupRows);
    const latest = groupRows
      .map(row => row.date)
      .filter(Boolean)
      .sort()
      .pop();
    const successRate = groupRows.length ? (stats.success / groupRows.length) * 100 : 0;
    return { runner, model, reasoning, rows: groupRows, stats, best, latest, successRate };
  }).sort((a, b) => {
    const reward = (b.best?.reward ?? -1) - (a.best?.reward ?? -1);
    if (reward) return reward;
    const success = b.successRate - a.successRate;
    if (success) return success;
    return `${a.runner} ${a.model}`.localeCompare(`${b.runner} ${b.model}`);
  });
}

function harnessModelTable(rows) {
  const groups = buildHarnessModelGroups(rows);
  const body = groups.map(group => {
    const cleanRate = group.rows.length ? (group.stats.clean / group.rows.length) * 100 : 0;
    return `<tr class="harness-row">
      <td><strong>${esc(group.runner)}</strong><div class="muted">${esc(group.model)}${group.reasoning ? ` / ${esc(group.reasoning)}` : ""}</div></td>
      <td>${number(group.rows.length)}</td>
      <td>${number(group.stats.success)} <span class="muted">(${pct.format(group.successRate)}%)</span></td>
      <td>${number(group.stats.scored)}</td>
      <td>${number(group.stats.clean)} <span class="muted">(${pct.format(cleanRate)}%)</span></td>
      <td>${group.best ? number(group.best.reward) : '<span class="muted">-</span>'}</td>
      <td>${group.best ? quality(group.best) : '<span class="muted">-</span>'}</td>
      <td>${esc(group.latest || "")}</td>
      <td>${trackList(group.rows)}</td>
    </tr>
    <tr class="group-details-row"><td colspan="9">${groupRunDetails(group.rows)}</td></tr>`;
  }).join("");
  return `<div class="table-wrap">
    <div class="table-title"><h3>Harness + Model Results</h3><span>${number(groups.length)} combinations</span></div>
    <table>
      <thead><tr><th>Harness / Model</th><th>Runs</th><th>Success</th><th>Scored</th><th>Source Clean</th><th>Best Reward</th><th>Best Quality</th><th>Latest</th><th>Tracks</th></tr></thead>
      <tbody>${body}</tbody>
    </table>
  </div>`;
}

function runTable(rows) {
  const body = sortedRuns(rows).map(row => `<tr>
    <td>${esc(row.date || "")}</td>
    <td><strong>${esc(row.runner)}</strong><div class="muted">${esc(row.model)}${row.reasoning ? ` / ${esc(row.reasoning)}` : ""}</div></td>
    <td><span class="track-name">${esc(row.track)}</span><div class="muted">${esc(row.practiceMode || row.workspaceMode || "")}</div></td>
    <td>${statusPill(row.status)}<div class="muted">${esc(row.outcome || "")}</div></td>
    <td>${row.reward === null || row.reward === undefined ? '<span class="muted">-</span>' : number(row.reward)}</td>
    <td>${quality(row)}</td>
    <td>${budgetCell(row)}</td>
    <td>${sourceCell(row)}</td>
    <td>${seconds(row.wallClockSec)}</td>
    <td class="mono">${esc(row.gameId || row.trajectory || "")}</td>
  </tr>`).join("");
  return `<details class="table-wrap table-details">
    <summary class="table-title"><h3>Run Results</h3><span>${number(rows.length)} rows</span></summary>
    <div class="details-table-scroll">
    <table>
      <thead><tr><th>Date</th><th>Runner / Model</th><th>Track</th><th>Status</th><th>Reward</th><th>Quality</th><th>Budget</th><th>Source</th><th>Wall</th><th>Game / Hash</th></tr></thead>
      <tbody>${body}</tbody>
    </table>
    </div>
  </details>`;
}

function renderEnvSection(env, rows) {
  const stats = envStats(rows);
  const successRate = stats.runs ? (stats.success / stats.runs) * 100 : 0;
  const cleanRate = stats.runs ? (stats.clean / stats.runs) * 100 : 0;
  return `<section class="env-section" style="--env-accent:${esc(env.accent)}">
    <div class="env-heading">
      <div>
        <h2>${esc(env.name)}</h2>
        <p>${esc(env.tagline)}</p>
      </div>
      <div class="env-stats">
        <div class="small-stat"><strong>${number(stats.runs)}</strong><span class="muted">runs</span></div>
        <div class="small-stat"><strong>${number(stats.success)}</strong><span class="muted">${pct.format(successRate)}% success</span></div>
        <div class="small-stat"><strong>${number(stats.clean)}</strong><span class="muted">${pct.format(cleanRate)}% clean</span></div>
        <div class="small-stat"><strong>${number(stats.bestReward)}</strong><span class="muted">best reward</span></div>
      </div>
    </div>
    <div class="notes">${(env.notes || []).map(note => `<div class="note">${esc(note)}</div>`).join("")}</div>
    <div class="tables">${trackTable(env.id, rows)}${harnessModelTable(rows)}${runTable(rows)}</div>
  </section>`;
}

function render() {
  const rows = filteredRuns();
  renderSummary(rows);
  const container = document.querySelector("#envSections");
  const envIds = Object.keys(data.environments).filter(envId => !state.env || state.env === envId);
  const sections = envIds.map(envId => {
    const envRows = rows.filter(row => row.env === envId);
    if (!envRows.length) return "";
    return renderEnvSection(data.environments[envId], envRows);
  }).filter(Boolean);
  container.innerHTML = sections.length ? sections.join("") : '<div class="empty">No results match the active filters.</div>';
}

populateControls();
render();
"""


def build(playground_root: Path, output_dir: Path) -> dict[str, Any]:
    track_to_env, track_meta, env_payload = load_env_track_index(playground_root)
    runs = collect_runs(playground_root, track_to_env, track_meta)
    payload = summarize(runs, env_payload)
    write_text(output_dir / "index.html", render_index())
    write_text(output_dir / "styles.css", render_css())
    write_text(output_dir / "app.js", render_js())
    data_text = "window.PLAYGROUND_RESULTS = " + json.dumps(payload, indent=2, ensure_ascii=False) + ";\n"
    write_text(output_dir / "data.js", data_text)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static GitHub Pages output for playground test results.")
    parser.add_argument("--playground-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "docs" / "playground-results")
    args = parser.parse_args()
    payload = build(args.playground_root.resolve(), args.output_dir.resolve())
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "runs": payload["summary"]["runCount"],
                "environments": payload["summary"]["envCount"],
                "latest_date": payload["summary"]["latestDate"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
