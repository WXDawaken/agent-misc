export type SceneId = string;
export type ObjectId = string;
export type Vec3 = [number, number, number];

export type RenderPass = "rgb" | "wireframe" | "flat" | "mask" | "depth" | "normal";
export type StandardView = "front" | "back" | "left" | "right" | "top" | "bottom" | "iso";

export interface Bounds {
  min: Vec3;
  max: Vec3;
  center: Vec3;
  size: Vec3;
}

export interface CameraSpec {
  position: Vec3;
  target: Vec3;
  up?: Vec3;
  fovDegrees?: number;
  near?: number;
  far?: number;
}

export interface ResolvedCameraSpec {
  position: Vec3;
  target: Vec3;
  up: Vec3;
  fovDegrees: number;
  near: number;
  far: number;
}

export interface RenderOptions {
  width?: number;
  height?: number;
  pass?: RenderPass;
  transparentBackground?: boolean;
  showGrid?: boolean;
  showAxes?: boolean;
  outputDir?: string;
}

export interface ImageResult {
  imagePath: string;
  width: number;
  height: number;
  camera: ResolvedCameraSpec;
  pass: RenderPass;
  visibleObjects: ObjectId[];
  nonblank: boolean;
  warnings: string[];
}

export interface LoadSceneRequest {
  source: string;
  formatHint?: "gltf" | "glb" | "auto";
}

export interface LoadSceneResponse {
  sceneId: SceneId;
  rootObjectId: ObjectId;
  units?: string;
  bounds: Bounds;
  warnings: string[];
}

export interface SceneObjectSummary {
  id: ObjectId;
  name?: string;
  type: string;
  parentId?: ObjectId;
  bounds?: Bounds;
  materialNames: string[];
  visible: boolean;
}

export interface SceneSummaryRequest {
  sceneId: SceneId;
  includeMaterials?: boolean;
  includeHierarchy?: boolean;
}

export interface SceneSummaryResponse {
  sceneId: SceneId;
  objectCount: number;
  triangleCount: number;
  bounds: Bounds;
  objects: SceneObjectSummary[];
  warnings: string[];
}

export interface RenderViewRequest {
  sceneId: SceneId;
  camera: CameraSpec;
  options?: RenderOptions;
}

export interface ViewGridRequest {
  sceneId: SceneId;
  targetObjectId?: ObjectId;
  views?: StandardView[];
  distanceScale?: number;
  options?: RenderOptions;
  contactSheet?: boolean;
}

export interface ViewGridResponse {
  images: ImageResult[];
  contactSheetPath?: string;
  warnings: string[];
}

export interface ObservationPackContactSheet {
  pass: RenderPass;
  contactSheetPath: string;
}

export interface ObservationPackRequest extends ViewGridRequest {
  includeSummary?: boolean;
  passes?: RenderPass[];
}

export interface ObservationPackResponse {
  sceneId: SceneId;
  summary?: SceneSummaryResponse;
  passes: RenderPass[];
  images: ImageResult[];
  contactSheetPath?: string;
  contactSheets?: ObservationPackContactSheet[];
  warnings: string[];
}

export interface MeasureEndpoint {
  point?: Vec3;
  objectId?: ObjectId;
}

export interface MeasureRequest {
  sceneId: SceneId;
  a: MeasureEndpoint;
  b: MeasureEndpoint;
  mode?: "center" | "closest_bounds" | "point";
}

export interface MeasureResponse {
  distance: number;
  units?: string;
  a: Vec3;
  b: Vec3;
  mode: "center" | "closest_bounds" | "point";
  warnings: string[];
}

export interface PickRequest {
  sceneId: SceneId;
  camera: CameraSpec;
  imageX: number;
  imageY: number;
  width: number;
  height: number;
}

export interface PickResponse {
  hit: boolean;
  objectId?: ObjectId;
  point?: Vec3;
  normal?: Vec3;
  distance?: number;
  warnings: string[];
}

export interface SetVisibilityRequest {
  sceneId: SceneId;
  objectId: ObjectId;
  visible: boolean;
  recursive?: boolean;
}

export interface SetVisibilityResponse {
  objectId: ObjectId;
  visible: boolean;
  recursive: boolean;
  changedObjectIds: ObjectId[];
  warnings: string[];
}

export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id?: string | number | null;
  method: string;
  params?: unknown;
}

export interface JsonRpcSuccess {
  jsonrpc: "2.0";
  id: string | number | null;
  result: unknown;
}

export interface JsonRpcFailure {
  jsonrpc: "2.0";
  id: string | number | null;
  error: {
    code: number;
    message: string;
    data?: unknown;
  };
}

export type JsonRpcResponse = JsonRpcSuccess | JsonRpcFailure;
