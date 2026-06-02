---
id: examples.arcane_lab.runner
engine: mini-mustache
default_variant: standard
description: "Small example of a runner prompt artifact for Arcane Lab."
inputs:
  workspace: string
  model: string
  tick_budget: int
  soft_stop_tick: int
  allowed_docs: list
  report_path: string
partials:
  runner_header: partials/runner_header.prompt.md
tags: [example, playground, runner]
---
{{> runner_header}}

{{#variant "standard"}}Hard rules:

- Use only the runner-provided workspace.
- Do not modify game code or data files.
- You may write only under `logs\`.
- At lifetime tick `{{soft_stop_tick}}` or later, stop progression commands.
{{/variant}}{{#variant "strict"}}Hard rules:

- Use only the runner-provided workspace.
- Do not modify game code, data files, or runner artifacts.
- You may write only under `logs\`.
- At lifetime tick `{{soft_stop_tick}}` or later, stop progression commands.
- Do not inspect or print runner auth environment variables.
{{/variant}}
Allowed reading:
{{#allowed_docs}}- `{{.}}`
{{/allowed_docs}}

Write the final report to `{{report_path}}`.
