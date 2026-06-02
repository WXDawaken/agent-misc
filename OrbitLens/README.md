# OrbitLens

OrbitLens is an agent-native 3D viewer concept: a programmable camera,
renderer, and geometry-query surface that lets agents with 2D vision inspect
3D models and scenes from controlled viewpoints.

The core idea is simple: keep the agent's existing image understanding path,
but give it reliable control over how 3D content is rendered into images.
OrbitLens should provide views, camera metadata, object structure, and auxiliary
passes such as depth, normal, wireframe, and masks.

## Current MVP

- TypeScript local service with a small JSON-RPC dispatcher and HTTP server.
- Three.js renderer hosted in a persistent browser/headless Chromium page.
- Local `.gltf` and `.glb` scene loading.
- Scene summaries with object ids, hierarchy hints, bounds, material names, and
  triangle counts.
- Explicit camera renders through `render_view`.
- Canonical multi-view grids through `view_grid`.
- Agent observation packs through `observation_pack`, including summary,
  multi-pass canonical renders, per-image camera metadata, visible object ids,
  nonblank checks, and optional per-pass contact sheets.
- Geometry measurements through `measure`, including point-to-point, object
  center, and closest-bounds modes.
- Pixel-to-scene picking through `pick`, returning hit object ids, 3D points,
  normals, and ray distance.
- Visibility control through `set_visibility`, useful for hiding occluders or
  isolating objects before rendering, picking, or measuring.
- Render passes for `rgb`, `flat`, `wireframe`, `mask`, `depth`, and `normal`.
- Scale-aware default camera fitting: OrbitLens preserves original scene units,
  but plans canonical cameras from each target's bounding-box diagonal so tiny
  and large models both fill the viewport by default.

## Docs

- [Implementation Route](docs/implementation-route.md)
- [Tool Contract Draft](docs/tool-contract.md)
- [MCP / Plugin Wrapper Notes](docs/mcp-plugin-wrapper.md)

## Quick Start

Install dependencies:

```powershell
npm install
```

Build and run tests:

```powershell
npm test
```

Run a smoke render against the bundled colored cube fixture:

```powershell
npm run smoke
```

Convert a ForgeCAD STL export into an OrbitLens-loadable GLB:

```powershell
forgecad export stl forgecad-tests\2026\05\25\orbitlens-test-bracket.forge.js --output forgecad-tests\2026\05\25\orbitlens-test-bracket.stl --quality high
node scripts\stl-to-glb.mjs forgecad-tests\2026\05\25\orbitlens-test-bracket.stl forgecad-tests\2026\05\25\orbitlens-test-bracket.glb
```

For colored ForgeCAD models, export 3MF and convert that to GLB:

```powershell
forgecad export 3mf forgecad-tests\2026\06\01\toy-monkey.forge.js --output forgecad-tests\2026\06\01\toy-monkey.3mf --quality high
node scripts\3mf-to-glb.mjs forgecad-tests\2026\06\01\toy-monkey.3mf forgecad-tests\2026\06\01\toy-monkey-colored.glb
```

The ForgeCAD conversion helpers map ForgeCAD's Z-up coordinates to glTF/Three's
Y-up convention by default so OrbitLens canonical views stay intuitive. Pass
`--preserve-up` when converting a source that is already Y-up.

Start the local JSON-RPC HTTP service:

```powershell
npm run build
node dist/src/cli.js serve --port 3987
```

Example JSON-RPC request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "load_scene",
  "params": {
    "source": "fixtures/colored-cube.gltf"
  }
}
```

## Preferred MVP

The first prototype follows the planned route: a TypeScript service with
Three.js running inside a browser/headless Chromium renderer. That keeps the
path close to an interactive viewer, provides fast multi-angle rendering, and
leaves room for a later Blender adapter when high-fidelity import or offline
rendering is needed.

Generated renders are written under `.orbitlens/` by default and are ignored by
Git.

## Default Scale

OrbitLens does not mutate or normalize model geometry after loading. Scene
summaries continue to report the original glTF/GLB coordinate values.

For viewing, canonical cameras use the target bounds as an observation scale:

- radius = half of the bounding-box diagonal
- distance = `radius / sin(fov / 2) * 1.25`
- near/far planes are derived from the same radius and camera distance

The `distanceScale` parameter remains available for deliberate close-ups or
wide establishing shots, but common small assets such as the Khronos Avocado
sample now render at a useful default size without manual tuning.
