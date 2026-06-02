# OrbitLens Tool Contract Draft

This is a draft contract for an agent-facing 3D viewer tool. Method names and
payloads should stay small, explicit, and easy to wrap as MCP tools.

## Core Types

```ts
type SceneId = string;
type ObjectId = string;

type Vec3 = [number, number, number];

interface CameraSpec {
  position: Vec3;
  target: Vec3;
  up?: Vec3;
  fovDegrees?: number;
  near?: number;
  far?: number;
}

interface RenderOptions {
  width?: number;
  height?: number;
  pass?: "rgb" | "wireframe" | "mask" | "flat" | "depth" | "normal";
  transparentBackground?: boolean;
  showGrid?: boolean;
  showAxes?: boolean;
  outputDir?: string;
}

interface ImageResult {
  imagePath: string;
  width: number;
  height: number;
  camera: Required<CameraSpec>;
  pass: string;
  visibleObjects?: ObjectId[];
  nonblank: boolean;
  warnings?: string[];
}
```

Depth is emitted as a grayscale view from the current camera depth buffer.
Normal is emitted as RGB world-space normals mapped from `[-1, 1]` to `[0, 1]`.

## Methods

### `load_scene`

Load a local file or URL into the scene registry.

```ts
interface LoadSceneRequest {
  source: string;
  formatHint?: "gltf" | "glb" | "obj" | "stl" | "ply" | "auto";
}

interface LoadSceneResponse {
  sceneId: SceneId;
  rootObjectId: ObjectId;
  units?: string;
  bounds: { min: Vec3; max: Vec3; center: Vec3; size: Vec3 };
  warnings?: string[];
}
```

### `scene_summary`

Return structured scene information before asking the vision model to inspect
images.

```ts
interface SceneSummaryRequest {
  sceneId: SceneId;
  includeMaterials?: boolean;
  includeHierarchy?: boolean;
}

interface SceneSummaryResponse {
  sceneId: SceneId;
  objectCount: number;
  triangleCount?: number;
  bounds: { min: Vec3; max: Vec3; center: Vec3; size: Vec3 };
  objects: Array<{
    id: ObjectId;
    name?: string;
    parentId?: ObjectId;
    bounds?: { min: Vec3; max: Vec3; center: Vec3; size: Vec3 };
    materialNames?: string[];
    visible: boolean;
  }>;
  warnings?: string[];
}
```

### `render_view`

Render one explicit camera view.

```ts
interface RenderViewRequest {
  sceneId: SceneId;
  camera: CameraSpec;
  options?: RenderOptions;
}

type RenderViewResponse = ImageResult;
```

### `view_grid`

Render a standard set of views for first-pass visual inspection.

```ts
interface ViewGridRequest {
  sceneId: SceneId;
  targetObjectId?: ObjectId;
  views?: Array<"front" | "back" | "left" | "right" | "top" | "bottom" | "iso">;
  distanceScale?: number;
  options?: RenderOptions;
  contactSheet?: boolean;
}

interface ViewGridResponse {
  images: ImageResult[];
  contactSheetPath?: string;
  warnings?: string[];
}
```

If `distanceScale` is omitted, OrbitLens uses scale-aware camera fitting. It
preserves original scene geometry, computes the target radius as half of the
bounding-box diagonal, and places canonical cameras at
`radius / sin(fov / 2) * 1.25`.

### `observation_pack`

Return a first-pass bundle meant for vision-agent inspection: scene summary,
canonical renders, camera metadata, visible object ids, nonblank render status,
warnings, and an optional contact sheet.

```ts
interface ObservationPackRequest extends ViewGridRequest {
  includeSummary?: boolean;
  passes?: Array<"rgb" | "wireframe" | "mask" | "flat" | "depth" | "normal">;
}

interface ObservationPackContactSheet {
  pass: "rgb" | "wireframe" | "mask" | "flat" | "depth" | "normal";
  contactSheetPath: string;
}

interface ObservationPackResponse {
  sceneId: SceneId;
  summary?: SceneSummaryResponse;
  passes: Array<"rgb" | "wireframe" | "mask" | "flat" | "depth" | "normal">;
  images: ImageResult[];
  contactSheetPath?: string;
  contactSheets?: ObservationPackContactSheet[];
  warnings?: string[];
}
```

If `passes` is omitted, `observation_pack` keeps the legacy behavior and uses
`options.pass` or `rgb`. If multiple passes are requested, OrbitLens renders
every requested `pass x view` combination, returns all images in pass-major
order, and writes one optional contact sheet per pass. `contactSheetPath`
remains as the first contact sheet path for older callers.

### `orbit_view`

Render a camera placed on a sphere around a scene or object target.

```ts
interface OrbitViewRequest {
  sceneId: SceneId;
  targetObjectId?: ObjectId;
  azimuthDegrees: number;
  elevationDegrees: number;
  distanceScale?: number;
  options?: RenderOptions;
}

type OrbitViewResponse = ImageResult;
```

### `focus_object`

Return a suggested camera for inspecting an object.

```ts
interface FocusObjectRequest {
  sceneId: SceneId;
  objectId: ObjectId;
  preferredDirection?: Vec3;
  padding?: number;
}

interface FocusObjectResponse {
  camera: Required<CameraSpec>;
  objectBounds: { min: Vec3; max: Vec3; center: Vec3; size: Vec3 };
  warnings?: string[];
}
```

### `set_visibility`

Hide or show objects for occlusion-free inspection.

```ts
interface SetVisibilityRequest {
  sceneId: SceneId;
  objectId: ObjectId;
  visible: boolean;
  recursive?: boolean;
}

interface SetVisibilityResponse {
  objectId: ObjectId;
  visible: boolean;
  recursive: boolean;
  changedObjectIds: ObjectId[];
  warnings: string[];
}
```

The MVP implements `set_visibility` through the service and JSON-RPC. By
default it applies recursively to the requested object subtree.

### `pick`

Map an image pixel back to the scene using object ids and approximate 3D
coordinates.

```ts
interface PickRequest {
  sceneId: SceneId;
  camera: CameraSpec;
  imageX: number;
  imageY: number;
  width: number;
  height: number;
}

interface PickResponse {
  hit: boolean;
  objectId?: ObjectId;
  point?: Vec3;
  normal?: Vec3;
  distance?: number;
  warnings: string[];
}
```

The MVP implements `pick` through the service and JSON-RPC using a Three.js
raycaster in the persistent renderer page. Pixel coordinates are measured from
the top-left corner of the rendered image.

### `measure`

Measure distances between points, picked hits, or object bounds.

```ts
interface MeasureRequest {
  sceneId: SceneId;
  a: { point?: Vec3; objectId?: ObjectId };
  b: { point?: Vec3; objectId?: ObjectId };
  mode?: "center" | "closest_bounds" | "point";
}

interface MeasureResponse {
  distance: number;
  units?: string;
  a: Vec3;
  b: Vec3;
  mode: "center" | "closest_bounds" | "point";
  warnings: string[];
}
```

The MVP implements `measure` through the service and JSON-RPC. `point` mode
requires explicit `point` endpoints. Default `center` mode resolves `objectId`
endpoints to object bounds centers. `closest_bounds` clamps the opposite
endpoint/reference point to the target object's bounds.

## Agent Observation Loop

1. Call `load_scene`.
2. Call `scene_summary` to understand names, bounds, and scale.
3. Call `view_grid` for canonical visual coverage.
4. Use 2D vision on the returned images.
5. Call `orbit_view`, `focus_object`, or `render_view` for uncertain details.
6. Use `mask`, `wireframe`, `depth`, or hidden-object views when RGB is
   ambiguous.
7. Use `pick` and `measure` for precise spatial claims.
