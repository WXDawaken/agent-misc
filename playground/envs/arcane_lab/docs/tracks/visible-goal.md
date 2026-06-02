---
id: playground.arcane_lab.tracks.visible-goal
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Visible Goal

Goal: complete `echo_vault_attuned` and craft `echo_anchor`, or get as close as
possible using only player-visible information and gradual goal disclosure.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

Track-specific play guidance:

- The target names are visible, but hidden conditions must be inferred through
  normal play.
- Do not assume retire/insight thresholds or route milestones until player-visible
  state points to them.
- Do not stop after a shallow early route if the visible goal is still plausible.

Before the final report, explicitly evaluate:

- `echo_vault_attuned` completed?
- `echo_anchor` owned?
- `echo_vault` unlocked and cleared?

Do not describe the run as successful unless `echo_vault_attuned` is complete
and `echo_anchor` is owned.

Verification:

At the end, call server-side `verify()` on the official game with no custom goal.
The token policy is authoritative.

Extra report fields:

- Whether `echo_vault_attuned` and `echo_anchor` were achieved.
- Feedback on goal clarity.
