# OrbitLens Implementation Route

## Goal

Build a local 3D observation tool for agents that already have 2D vision. The
tool should let an agent load a 3D asset or scene, request controlled camera
views, inspect scene structure, and ask for targeted render passes when normal
RGB views are ambiguous.

## Recommended Architecture

Start with a TypeScript service and a Three.js renderer hosted in a persistent
browser context or headless Chromium process. Keep the tool protocol separate
from the renderer so a Blender or Open3D backend can be added later.

```text
agent/tool caller
  -> JSON-RPC or MCP wrapper
  -> OrbitLens service
     -> scene registry
     -> camera planner
     -> Three.js render backend
     -> geometry query helpers
     -> image/artifact store
```

## Current Implementation

The MVP now follows this architecture:

- `src/service/orbitLensService.ts` owns scene registration, file loading,
  camera planning, render output paths, contact sheets, and observation packs.
- `src/renderer/browserRenderer.ts` starts a persistent Chromium-family browser
  through Playwright and serves `renderer.html` plus `node_modules` from a
  local read-only static server.
- `src/renderer/renderer.html` runs Three.js and `GLTFLoader`, keeps scenes in
  browser memory, computes summaries, and renders RGB, flat, wireframe, mask,
  depth, and normal passes.
- `src/server/jsonRpc.ts` and `src/server/httpServer.ts` expose the local
  JSON-RPC surface.
- `fixtures/colored-cube.gltf` is the checked-in fixture; tests also generate a
  temporary GLB to verify the binary path.
- `tests/` covers camera planning, glTF and GLB loading, scene summaries,
  nonblank PNG render output, view grids, contact sheets, single-pass and
  multi-pass `observation_pack`, and the JSON-RPC surface.

## Why This Route

- Three.js gives a direct path to glTF/GLB, camera controls, object picking, and
  browser preview.
- Headless Chromium keeps multi-view rendering close to what an interactive UI
  would show.
- The service can return both images and structured metadata, which is crucial
  for agents that must reason about observations over multiple turns.
- Blender can be added as a second backend for FBX/USD conversion, complex
  materials, path-traced stills, or scenes that Three.js cannot load cleanly.

## Directory Shape

```text
OrbitLens/
  README.md
  docs/
    implementation-route.md
    tool-contract.md
  src/
    server/
    renderer/
    camera/
    scene/
    passes/
  fixtures/
  tests/
```

Only the docs exist in this first pass. Add source folders when the prototype
starts, so empty scaffolding does not imply finished implementation.

## MVP Milestones

1. Service skeleton
   - Done: local JSON-RPC dispatcher and HTTP server are implemented.
   - Done: `load_scene`, `scene_summary`, `render_view`, `view_grid`, and
     `observation_pack` are implemented.
   - Done: local GLB/glTF files are supported and tested.

2. Three.js render backend
   - Done: one browser/renderer process stays alive across calls.
   - Done: world-space bounds are computed from loaded Three.js scenes.
   - Done: PNG images are written with camera metadata.
   - Done: every render is checked for nonblank output.

3. Camera planner
   - Done: canonical views include front, back, left, right, top, bottom, and
     isometric.
   - Done: default camera distance is scale-aware and derived from the target
     bounding-box diagonal, with no one-unit floor for small models.
   - Partial: `view_grid` can target scene or object bounds.
   - Planned: explicit `orbit_view` and `focus_object` methods.

4. Agent observation pack
   - Done: `observation_pack` produces per-view images and contact sheets.
   - Done: `observation_pack` can render multiple utility passes in one call.
   - Done: image results include camera pose, target point, FOV, visible object
     ids, nonblank status, and warnings.
   - Planned: richer follow-up close-up helpers.

5. Utility render passes
   - Done: RGB, wireframe, flat material, object-mask, depth, and normal passes.

6. Geometry queries
   - Done: `pick` maps image pixels back to object ids plus approximate 3D
     points, normals, and ray distance.
   - Done: `measure` supports point-to-point, object-center, and closest-bounds
     distance queries.
   - Done: `set_visibility` hides or shows objects recursively for occlusion-free
     inspection.

7. MCP/plugin surface
   - Documented: see `docs/mcp-plugin-wrapper.md`.
   - Planned: implement an actual MCP server wrapper once the MVP surface has
     had a little usage.

8. Blender fallback
   - Add optional asset conversion for formats beyond glTF/GLB.
   - Add high-quality still rendering for difficult material or lighting cases.
   - Keep Blender out of the required MVP path.

## First Test Fixtures

- A colored cube with known dimensions and face colors.
- A two-object occlusion scene for visibility and mask checks.
- A simple room-like scene for camera planning and wide/narrow FOV checks.
- A tiny GLB with named meshes and nested transforms.

## Verification Strategy

- Unit-test bounds, camera poses, and method schemas.
- Render the cube fixture from canonical views and assert nonblank images.
- Validate that picking the center of a rendered cube face returns the expected
  object id.
- Compare object-mask pass colors against the scene registry.
- Use a browser screenshot during UI work to catch framing and overlap issues.

Current verification command:

```powershell
npm test
```

Current smoke command:

```powershell
npm run smoke
```

## Open Design Questions

- Whether the first public surface should be MCP-only or JSON-RPC plus MCP.
- How much persistent scene state should survive between tool calls.
- Whether observation packs should be returned as a single contact sheet, a
  list of separate images, or both.
- How to represent uncertainty: renderer warnings, coverage estimates, or
  explicit "needs another view" hints.
