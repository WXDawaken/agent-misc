# Promptkit First Pass

## Goal

Create a small prompt artifact layer for this workspace without inventing a full
prompt DSL.

The first pass standardizes:

- prompt files with front matter plus markdown body
- a minimal mustache-like renderer
- variable loading from JSON or TOML
- linting for missing inputs and simple type mismatches
- reproducible rendered snapshots
- partial includes, named variants, and a JSON IR compile step

## Paths

- Tooling: `E:\agent_misc\promptkit`
- Shared prompt artifacts: `E:\agent_misc\prompts`
- Example prompt: `E:\agent_misc\prompts\examples\arcane_lab_runner.prompt.md`

## Commands

Render an example prompt:

```powershell
python -m promptkit.render render prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json
```

Lint it:

```powershell
python -m promptkit.render lint prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json
```

Write a snapshot:

```powershell
python -m promptkit.render snapshot prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json --out-dir .prompt_snapshots
```

Render a named variant:

```powershell
python -m promptkit.render render prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json --variant strict
```

Compile to JSON IR:

```powershell
python -m promptkit.render compile prompts\examples\arcane_lab_runner.prompt.md
```

Run the smoke tests:

```powershell
python -m unittest promptkit.test_promptkit -v
```

## Format

Prompt files use a conservative YAML-like front matter subset:

```md
---
id: examples.arcane_lab.runner
engine: mini-mustache
inputs:
  workspace: string
  tick_budget: int
---

Use `{{workspace}}` with budget `{{tick_budget}}`.
```

Supported input types are `string`, `int`, `float`, `number`, `bool`, `list`,
`object`, and `any`.

The first renderer supports:

- variables: `{{name}}`, `{{nested.value}}`, `{{.}}`
- list/object/truthy sections: `{{#items}}...{{/items}}`
- inverted sections: `{{^items}}...{{/items}}`
- partial includes: `{{> runner_header}}`
- named variants: `{{#variant "strict"}}...{{/variant}}`
- comments: `{{! comment }}` and `{{!-- block comment --}}`

The renderer intentionally does not execute arbitrary expressions or shell out.

## Parasitic DSL Boundaries

Promptkit is now a small parasitic DSL over markdown, front matter, and a
mustache-like template subset.

It should keep these responsibilities:

- declare prompt metadata, inputs, partials, variants, and target-facing notes
- render deterministic text from a prepared variable object
- compile a prompt artifact into JSON IR for inspection, diffing, and future eval
  adapters

It should not absorb these responsibilities:

- arbitrary expression evaluation
- shell command execution
- mailbox protocol/runtime semantics
- agent orchestration logic
- model-provider-specific execution policy

The working rule is: prepare complex context in Python or runner scripts; keep
promptkit focused on prompt structure, rendering, linting, and reproducible
artifacts.

## Migration Notes

Good first migration candidates:

- `playground\scripts\run_opencode_go_playtest.ps1` (migrated: renders shared
  and track prompts through promptkit and records vars/lint/rendered artifacts
  under each `.runner` directory)
- `playground\scripts\run_deepseek_claude_playtest.ps1` (migrated: renders the
  selected DeepSeek Claude prompt through promptkit and records vars/lint/rendered
  artifacts under each `.runner` directory)
- `benchmarks\run_codex_benchmark.py`
- `benchmarks\run_ollama_codegen_eval.py`

The recommended migration pattern is to render the prompt through `promptkit`,
write `rendered.md` into each runner's existing artifact directory, and keep the
current runner-specific launch mechanics unchanged.
