# Agent Experiment Lab

中文 | [English](README.md)

这是一个用于研究 coding agent 行为的实验仓库，覆盖 prompt artifact 渲染、benchmark 编排、subagent 工作流，以及交互式文字游戏环境。

这个仓库更像实验室，而不是打磨完成的产品。它把小而可检查的工具和对应 workload 放在一起，方便复现实验、审阅结果，并在不引入大型服务栈的情况下继续调整。

## 目录概览

- `benchmarks/`：benchmark runner、任务定义、workspace manifest、dashboard 工具，以及人工质量评审后的分析脚本。
- `promptkit/`：一个只依赖 Python 标准库的小型 prompt artifact 渲染器和 linter，面向 markdown 加 front matter 的 prompt 文件。
- `prompts/`：可复用的 prompt artifact 和示例变量文件。
- `OrbitLens/`：agent-native 3D viewer MVP，让带 2D vision 的 agent 通过可控的 Three.js/Chromium 渲染观察 glTF/GLB 场景。
- `playground/`：`Arcane Lab`，一个原创的、确定性的文字 RPG 环境，用来测试长程规划、工具使用和失败恢复能力。
- `subagent_lab/`：Codex 原生 subagent 实验，以及 benchmark harness 使用的 `Salvage Run` 控制台 workload。
- `docs/`：适合随仓库共享的 benchmark 报告、设计笔记和实验 memo。
- `tools/`：本地辅助脚本和生成的索引。

部分本地 workspace handoff 文件、运行产物、日志、缓存和 sibling checkout 会被 Git 忽略。尤其是 `mail4agent`：它被视为独立的 sibling repo，而不是这个仓库的 submodule。

## Codex 环境说明

这个仓库主要是在 Codex 环境里开发和运行的。有些脚本假定 `codex` CLI 已经安装、完成认证，并且可以从 `PATH` 直接调用。像 `promptkit` 测试这样的纯 Python 工具不依赖 Codex；但 benchmark run、subagent 实验，以及部分 runner 脚本都围绕 Codex CLI 行为和本地 Codex 配置设计。

## 快速开始

大多数工具都是 Python 脚本，依赖很少。除非命令里明确切换目录，否则从仓库根目录运行即可。

运行 promptkit 测试：

```powershell
python -m unittest promptkit.test_promptkit -v
```

检查一个示例 prompt artifact：

```powershell
python -m promptkit.render lint prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json
```

列出 benchmark 任务：

```powershell
python benchmarks\run_codex_benchmark.py --list-tasks
```

预演一次 benchmark 调用：

```powershell
python benchmarks\run_codex_benchmark.py --task small_scan_hazard_warning --mode single_xhigh --mode subagents --repeat 1 --dry-run
```

运行 `Salvage Run` workload 测试：

```powershell
cd subagent_lab
python -m unittest test.test_salvage_run -v
```

运行 `Arcane Lab` 文字 RPG smoke 脚本：

```powershell
cd playground
python game.py --new --script scripts\smoke.txt
```

## Benchmark 形态

benchmark harness 会让不同 agent 执行模式在同一组隔离任务上对比。当前主要轨道包括：

- `single_xhigh`：一个高 reasoning effort 的 agent 直接完成任务。
- `subagents`：使用带角色分工的原生 subagent 工作流。
- 本地模型 code generation helper：用于非 agentic 的 patch 尝试。

harness 会记录 setup 时间、求解时间、token 用量、验证结果、变更文件摘要和最终回复。另有脚本可以构建盲评 packet，并在评审后分析 judged quality。

workspace materialization 支持基于复制的隔离和 Git worktree。脏本地实验适合用 copy backend；需要干净、commit-pinned baseline 时再用 Git worktree。

## Prompt Artifacts

`promptkit` 是一个刻意保持很小的层，建立在 markdown、front matter 和 mustache-like 模板子集之上。它支持：

- 声明输入和简单类型检查
- 变量渲染
- list/object/truthy section
- partial include
- named variant
- rendered snapshot
- JSON IR 编译

它不会执行任意表达式，也不会 shell out。复杂上下文组装应放在 Python 或 runner 脚本里，然后用 promptkit 渲染可复现的 prompt artifact。

## 安全说明

这个仓库用于本地 agent 实验，不是安全沙箱。agent 和 runner 可能会执行代码、写文件、检查 workspace 内容，并生成大量日志。运行不可信 agent 时，请使用隔离 workspace 和低权限凭据。

不要提交 secret、provider token、生成的 agent workspace、benchmark results、save 文件、日志、本地 Codex home，或 sibling repo 内容。根目录 `.gitignore` 已经尽量把这些挡在常规 Git 操作之外，但发布前仍然应该人工复查变更。

## 发布说明

预期的公开布局是一个 root repo，承载共享工具和 fixture：

- `subagent_lab/` 作为普通 tracked directory
- `mail4agent` 保持 sibling repo
- Git worktree 只用于临时 benchmark materialization，不作为永久 repo 结构
- 本地 workspace handoff 文档不追踪

第一次公开 commit 前，应清理或归档临时输出目录，并决定历史 benchmark 报告是否需要迁到单独的结果归档里。
