# MCP / Plugin Wrapper Notes

OrbitLens currently exposes a local JSON-RPC surface. The intended MCP or Codex
plugin wrapper should be thin: keep scene state and rendering in the existing
service, and map each stable JSON-RPC method to one agent tool.

## Wrapper Shape

Recommended tools:

- `orbitlens_load_scene`
- `orbitlens_scene_summary`
- `orbitlens_render_view`
- `orbitlens_view_grid`
- `orbitlens_observation_pack`
- `orbitlens_pick`
- `orbitlens_measure`
- `orbitlens_set_visibility`

The wrapper should return structured JSON for metadata and attach image paths
as artifacts or tool-result images, depending on the host capability.

## Method Mapping

| Tool | JSON-RPC Method | Purpose |
| --- | --- | --- |
| `orbitlens_load_scene` | `load_scene` | Load a `.gltf` or `.glb` scene and return ids/bounds. |
| `orbitlens_scene_summary` | `scene_summary` | Return object ids, names, bounds, materials, and triangle counts. |
| `orbitlens_render_view` | `render_view` | Render one explicit camera view. |
| `orbitlens_view_grid` | `view_grid` | Render canonical multi-view images and an optional contact sheet. |
| `orbitlens_observation_pack` | `observation_pack` | Return summary plus a multi-view render pack for vision analysis. |
| `orbitlens_pick` | `pick` | Map an image pixel and camera back to a scene object and 3D point. |
| `orbitlens_measure` | `measure` | Measure point-to-point, object-center, or closest-bounds distances. |
| `orbitlens_set_visibility` | `set_visibility` | Hide or show object subtrees before rendering, picking, or measuring. |

## Agent UX

For most agent workflows, `observation_pack` should be the first call after
`load_scene`. It gives the vision model enough coverage to decide whether it
needs a targeted follow-up render.

The wrapper should present returned image paths directly to the model whenever
the host supports image inputs. If the host only supports text, return the
metadata and contact sheet path so a second tool can attach the image.

## State Model

Keep scene state in the OrbitLens service process. MCP/tool wrappers should not
try to serialize Three.js scenes. They should pass `sceneId` values back into
the service and let the service own browser lifecycle, scene memory, and render
artifact paths.

## Near-Term Additions

- Add a stdio MCP server entrypoint once the JSON-RPC method names settle.
- Add `orbit_view` and `focus_object` wrappers after those methods exist in the
  service.
- Add ergonomic image-click plumbing in host integrations so agents can call
  `pick` from displayed images without manually copying pixel coordinates.
- Add explicit artifact cleanup controls for long-running agent sessions.
