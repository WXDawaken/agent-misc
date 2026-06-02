# Draft: Tool-Building Axis

This is a draft evaluation axis, not an active track.

Recent Codex 5.4 high playtests showed a distinct capability: the agent often
created a small helper or route runner before committing to official play. This
looked less like one-off scripting noise and more like deliberate experiment
harness construction. The behavior improved route reliability, reduced SDK
shape mistakes, and made official trajectories cleaner.

Because the current track set is already broad, do not add this as a separate
track yet. Keep it as an analysis label that can be applied to existing runs.

Possible labels:

- `tool-building allowed`: the current default. Agents may write helper scripts
  under `logs\` and use them for practice and official play.
- `command-only`: agents may call SDK/CLI commands directly but may not create
  helper scripts.
- `single-shot official`: agents may explore and plan, but the official game
  must be driven by one submitted command batch or one short final route file.

Suggested metrics:

- Number of helper files created.
- Whether helpers are generic SDK wrappers or hard-coded route scripts.
- Whether helper use reduced failed official actions.
- Whether helper use caused source-policy or auth-token mistakes.
- Ratio of practice exploration to official command count.

Use this axis when comparing models with similar final rewards but different
work styles. It should help distinguish route understanding from harness
construction without multiplying the active track count.
