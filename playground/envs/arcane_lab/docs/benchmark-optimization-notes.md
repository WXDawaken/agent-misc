# Arcane Lab Benchmark Optimization Notes

This document records benchmark improvements that are useful beyond a single
model run. Status is intentionally lightweight so the ideas can survive context
handoffs without becoming a second roadmap.

## Implemented

### Route Quality Scoring

Add a structured `route_quality` block to runner summaries so a successful run
can still be compared by route discipline. The score should not replace
official verification; it is an auxiliary lens for:

- hard-goal completion
- lifetime tick efficiency
- soft-stop compliance
- failed-command count
- source-policy compliance
- prestige/retirement target completion
- random crit occurrence signals for stability review

Random crit signals should be treated as a warning, not proof of route
dependence. A successful route that saw random crits should usually be rerun
with another seed before being considered stable.

Implemented on 2026-04-28 in `scripts/runner_common.py`, with Codex CLI and
OpenCode Go runner integration.

### Track Slimming And Layered Profiles

Keep all existing tracks, but expose named suites so routine model tests do not
always run the expensive discovery matrix. The default suite should be a compact
baseline; full and discovery suites remain available for deeper audits.

Current suite intent:

- `smoke`: shortest wiring and mechanics check
- `core`: routine baseline for most model comparisons
- `prestige`: route-oriented prestige variants, including crit-build eval
- `discovery`: blind and semi-blind exploration tracks
- `full`: all active tracks

Implemented on 2026-04-28 in `docs/tracks/config.json` and documented in
`docs/tracks/README.md`.

### Replay Review Enhancements

Improve the replay page with route-quality overlays, retirement markers,
failed-command highlights, soft-stop lines, and crit roll markers. This should
make post-run inspection faster without forcing readers into raw JSON.

Implemented on 2026-04-28 in `server.py`. The replay page now auto-loads
persisted verification, draws a route map with soft/hard budget lines and event
markers, adds timeline/frame badges, and computes a replay-side route quality
panel.

## Backlog

### No-Offline-Practice Tracks

Add tracks where `offline_practice=false`, server new-game count is limited, and
the direct SDK is absent. This separates planning under abundant local practice
from one-shot operational play.

### Observation And Prompt Stability

Keep the player-facing observation schema stable and document any intentional
new fields. Prompt changes should remain separated into shared and track-scoped
files so benchmark deltas can be attributed.

### Route Compression And Balance Audits

Periodically run reference and strong-agent routes against budget changes,
enhancement tuning, crit tuning, and boss counter tuning. Track whether the
benchmark is measuring agent strategy or just a brittle numeric threshold.

### Cross-Harness Comparability

Keep platform-specific runners thin and push preparation, prompt rendering,
summary collection, and scoring into common Python utilities. This reduces
differences between Codex CLI, OpenCode, Claude Code, and future harnesses.
