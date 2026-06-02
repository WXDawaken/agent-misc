# Prompt Artifacts

This folder is for reusable prompt artifacts rendered by `promptkit`.

Use markdown with a small YAML-like front matter block:

```md
---
id: example.prompt
engine: mini-mustache
inputs:
  workspace: string
---

Work in `{{workspace}}`.
```

Render with:

```powershell
python -m promptkit.render render prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json
```

Create a reproducible snapshot with:

```powershell
python -m promptkit.render snapshot prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json --out-dir .prompt_snapshots
```

Render a variant or compile JSON IR with:

```powershell
python -m promptkit.render render prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json --variant strict
python -m promptkit.render compile prompts\examples\arcane_lab_runner.prompt.md
```
