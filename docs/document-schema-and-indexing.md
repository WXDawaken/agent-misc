# Document Schema and Indexing

## Summary

Define a lightweight document schema so one canonical document can be discovered from multiple scopes without copying its body.

This workspace should treat Markdown docs as durable knowledge pages, while benchmark outputs and other generated artifacts remain raw sources that docs can point at.

## Index

- [Goal](#goal)
- [Content Model](#content-model)
- [Principles](#principles)
- [Minimal Frontmatter](#minimal-frontmatter)
- [On-Page Index Rule](#on-page-index-rule)
- [External Index Rules](#external-index-rules)
- [Repo Scope Taxonomy](#repo-scope-taxonomy)
- [Naming and Placement](#naming-and-placement)
- [Adoption Plan](#adoption-plan)
- [Tooling](#tooling)
- [Examples](#examples)

## Goal

- Keep one canonical body per document.
- Allow the same document to be indexed by workspace, domain, series, document type, and time.
- Make indexing cheap enough to maintain by hand or with LLM help.
- Avoid turning generated artifacts into pseudo-docs.

## Content Model

Use three document roles:

- Content doc: the canonical body for a plan, memo, report, eval, guide, rubric, spec, or prompt.
- Index doc: a navigation page that groups content docs by a scope such as a workspace, domain, or series.
- Raw artifact: generated results, dashboards, logs, or run directories. These stay outside the document index and are linked from docs when relevant.

This means:

- A content doc owns the explanation.
- An index doc owns discovery.
- A raw artifact owns the evidence payload.

## Principles

- One body, many entries: never duplicate a document's main text just because it belongs to multiple scopes.
- Metadata first: prefer explicit frontmatter over filename parsing.
- Facets over folders: use workspace, domain, and series as reusable dimensions instead of forcing one tree to do everything.
- Curated indexes are allowed: not every index has to be generated; some should present a reading order or a narrowed question.
- Backfill lazily: do not rewrite the entire docs tree at once. Add schema when a document is touched or promoted.

## Minimal Frontmatter

Every durable Markdown doc should start with YAML frontmatter.

Required fields:

- `id`: stable kebab-case identifier
- `title`: display title
- `type`: document kind
- `workspace`: owning workspace
- `domains`: one or more topic domains
- `status`: lifecycle state
- `created`: first creation date in `YYYY-MM-DD`

Recommended fields:

- `updated`: last meaningful content update date
- `series`: one or more recurring lines of work
- `summary`: one sentence summary

Optional fields:

- `related`: related document ids
- `supersedes`: older document ids replaced by this doc
- `artifact_paths`: raw artifact paths or directories that support this doc

Template:

```yaml
---
id: subagent-benchmark-plan
title: Subagent Benchmark Plan
type: plan
workspace: root
domains:
  - benchmark
  - subagents
series:
  - subagent-benchmark
status: active
created: 2026-03-19
updated: 2026-03-19
summary: Compare native subagent runs against a single high-effort agent on the same tasks.
related:
  - benchmark-judge-rubric
  - subagent-benchmark-report-20260319
supersedes: []
artifact_paths: []
---
```

Field rules:

- `id` should stay stable even if the title changes.
- Use the filename date only when the document is a dated point-in-time record, not a living page.
- `status` should be one of `draft`, `active`, `reference`, `superseded`, or `archived`.
- `type` should stay small and consistent. Prefer `plan`, `report`, `eval`, `memo`, `rubric`, `guide`, `spec`, `prompt`, `index`, or `sample`.

## On-Page Index Rule

Each durable content doc should include an `## Index` section near the top.

Rule:

- Put the `## Index` section after the opening summary.
- List the major headings in reading order.
- Keep it short, usually 4 to 8 entries.
- Every index entry should map to an actual section in the same file.

Example:

```md
## Index

- [Summary](#summary)
- [Context](#context)
- [Decision](#decision)
- [Evidence](#evidence)
- [Next](#next)
- [Related](#related)
```

Suggested section shapes by type:

- `plan`: `Summary`, `Goal`, `Scope`, `Decisions`, `Risks`, `Next`, `Related`
- `report` or `eval`: `Summary`, `Question`, `Setup`, `Findings`, `Evidence`, `Decision`, `Related`
- `memo`: `Summary`, `Context`, `Observation`, `Implication`, `Next`, `Related`
- `guide` or `spec`: `Summary`, `Model`, `Rules`, `Examples`, `Related`
- `prompt`: `Summary`, `Use`, `Prompt`, `Notes`, `Related`

## External Index Rules

External indexing should be metadata-driven first and curated second.

Primary scopes:

- `workspace`: where the doc belongs
- `domains`: what the doc is about
- `series`: what ongoing line it contributes to
- `type`: what kind of doc it is
- `created` and `updated`: when it matters in the timeline

Secondary link scopes:

- `related`: peer docs worth reading together
- `supersedes`: document lineage

Rules:

- A content doc may appear in multiple indexes.
- Index docs should link and summarize, not restate the full body.
- Domain index pages should exist only for domains with enough volume to justify them.
- Series pages should exist when there are at least two docs or when growth is expected.
- Curated docs may index other docs directly when a question-oriented reading order is more useful than a pure facet list.

## Repo Scope Taxonomy

Use a small fixed vocabulary first.

Recommended `workspace` values:

- `root`
- `subagent_lab`
- `mail4agent`
- `benchmarks`
- `judge_lab`

Recommended root-level `domains`:

- `benchmark`
- `subagents`
- `judge`
- `mail4agent`
- `docs-process`

Recommended `subagent_lab` `domains`:

- `subagents`
- `workload`
- `salvage-run`
- `game-engine`
- `anchor-agent`
- `validation`

Series should stay specific and reusable, for example:

- `subagent-benchmark`
- `subagent-web-port-large-task`
- `mail4agent-rust-feature-benchmark`
- `anchor-agent`
- `salvage-run-web-port`

## Naming and Placement

Keep the current document locations unless there is a strong reason to move them.

Placement rules:

- Root coordination docs stay under `E:\agent_misc\docs`.
- Native subagent experiment docs stay under `E:\agent_misc\subagent_lab\docs`.
- Raw benchmark artifacts stay under result directories and are referenced from docs instead of copied.

Filename rules:

- Living pages should prefer stable names without dates, for example `mainline-plan.md`.
- Point-in-time records should keep their date suffixes, for example `subagent-reviewer-agent-type-bug-20260331.md`.
- The `id` field is canonical for indexing; filenames can remain human-friendly.

Index page rules:

- Start with one workspace entry page per major docs area.
- Add domain pages only after there is enough density.
- Add series pages when a workstream clearly spans multiple docs.

## Adoption Plan

Use a low-friction rollout:

1. New durable docs should adopt the schema immediately.
2. Existing docs should be backfilled only when edited or promoted to a canonical reference.
3. Start with the highest-traffic docs:
   - `E:\agent_misc\docs\mainline-plan.md`
   - `E:\agent_misc\docs\subagent-benchmark-plan.md`
   - `E:\agent_misc\docs\benchmark-judge-rubric.md`
   - `E:\agent_misc\subagent_lab\docs\codex-subagents.md`
   - `E:\agent_misc\subagent_lab\docs\console-game-workload.md`
4. Once a few docs have frontmatter, add workspace index pages that link them.

Do not try to frontmatter every historical file in one pass.

## Tooling

The workspace now includes a lightweight metadata-aware indexer:

- `python E:\agent_misc\tools\doc_index.py scan`
- `python E:\agent_misc\tools\doc_index.py list --workspace root`
- `python E:\agent_misc\tools\doc_index.py list --domain subagents --verbose`
- `python E:\agent_misc\tools\doc_index.py show subagent-benchmark-plan`
- `python E:\agent_misc\tools\doc_index.py generate-scopes`
- `python E:\agent_misc\tools\doc_index.py rebuild-db`
- `python E:\agent_misc\tools\doc_index.py query-scope --scope-kind domain`
- `python E:\agent_misc\tools\doc_index.py add-curated-scope-member --scope-kind domain --scope-value custom-reading-list --doc-id root-mainline-plan`
- `python E:\agent_misc\tools\doc_index.py remove-curated-scope-member --scope-kind domain --scope-value custom-reading-list --doc-id root-mainline-plan`
- `python E:\agent_misc\tools\doc_index.py generate-scopes-from-db`

Behavior:

- By default the tool scans `docs/` plus any immediate child workspace that also has a `docs/` directory.
- It indexes docs that already have valid frontmatter.
- It also reports which docs are still missing frontmatter, so schema rollout can stay incremental.
- It can generate scope index pages under `docs/scopes/` directly from indexed frontmatter.
- It can also rebuild a SQLite index at `E:\agent_misc\tools\doc_index.sqlite3` for direct scope queries and DB-backed page generation.
- Use `--json` when another script or LLM step should consume the results directly.

Recommended default:

- Use `python E:\agent_misc\tools\doc_index.py rebuild-db` first.
- Then use `python E:\agent_misc\tools\doc_index.py generate-scopes-from-db --output-root docs\scopes`.
- Treat `docs/scopes/` as the canonical generated scope tree.
- Treat `generate-scopes` as a frontmatter-only fallback, not the main publishing path.

SQLite notes:

- `documents` stores indexed docs.
- `document_domains`, `document_series`, `document_related`, `document_supersedes`, and `document_artifact_paths` store normalized metadata edges.
- `scope_members` stores scope membership rows.
- Rows in `scope_members` with `source_type = 'generated'` are rebuilt from frontmatter.
- Rows in `scope_members` with `source_type = 'curated'` are left alone by `rebuild-db`, so they are the safe place for direct SQL inserts, updates, or deletes.
- The CLI now exposes `add-curated-scope-member` and `remove-curated-scope-member` so hand-maintained scope rows do not require manual SQL.

## Examples

Example metadata for a root planning doc:

```yaml
---
id: subagent-benchmark-plan
title: Subagent Benchmark Plan
type: plan
workspace: root
domains:
  - benchmark
  - subagents
series:
  - subagent-benchmark
status: active
created: 2026-03-19
updated: 2026-03-19
summary: Benchmark when native subagents are worth their coordination cost.
related:
  - benchmark-judge-rubric
---
```

Example metadata for a `subagent_lab` workload doc:

```yaml
---
id: console-game-workload
title: Console Game Workload
type: guide
workspace: subagent_lab
domains:
  - workload
  - salvage-run
  - game-engine
status: reference
created: 2026-03-19
updated: 2026-03-29
summary: Describe the Salvage Run gameplay workload and how to run it.
related:
  - codex-subagents
  - engine-salvage-cross-project-tasks-20260329
artifact_paths: []
---
```

Example metadata for a dated incident memo:

```yaml
---
id: subagent-reviewer-agent-type-bug-20260331
title: reviewer agent_type mismatch after desktop restart
type: memo
workspace: root
domains:
  - subagents
status: archived
created: 2026-03-31
updated: 2026-03-31
summary: Capture a reproducible mismatch between desktop and CLI agent type resolution.
related:
  - codex-subagents
---
```
