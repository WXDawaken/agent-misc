import type { Bounds, CameraSpec, ResolvedCameraSpec, StandardView, Vec3 } from "../types.js";

const DEFAULT_FOV = 45;
const DEFAULT_UP: Vec3 = [0, 1, 0];
const MIN_VIEW_RADIUS = 1e-6;
export const DEFAULT_DISTANCE_SCALE = 1.25;

export function resolveCamera(camera: CameraSpec, sceneBounds?: Bounds): ResolvedCameraSpec {
  const radius = Math.max(sceneBounds ? boundsRadius(sceneBounds) : distance(camera.position, camera.target), MIN_VIEW_RADIUS);
  const viewDistance = Math.max(distance(camera.position, camera.target), MIN_VIEW_RADIUS);
  const near = camera.near ?? Math.max(MIN_VIEW_RADIUS, Math.min(viewDistance * 0.05, radius * 0.1));
  const far = camera.far ?? Math.max(viewDistance + radius * 4, radius * 10, near * 100);

  return {
    position: camera.position,
    target: camera.target,
    up: camera.up ?? DEFAULT_UP,
    fovDegrees: camera.fovDegrees ?? DEFAULT_FOV,
    near,
    far
  };
}

export function cameraForStandardView(
  view: StandardView,
  bounds: Bounds,
  distanceScale = DEFAULT_DISTANCE_SCALE,
  fovDegrees = DEFAULT_FOV
): ResolvedCameraSpec {
  const center = bounds.center;
  const radius = Math.max(boundsRadius(bounds), MIN_VIEW_RADIUS);
  const distanceToFit = radius / Math.sin((fovDegrees * Math.PI / 180) / 2);
  const d = distanceToFit * distanceScale;
  const direction = directionForView(view);
  const position: Vec3 = [
    center[0] + direction[0] * d,
    center[1] + direction[1] * d,
    center[2] + direction[2] * d
  ];

  return resolveCamera({
    position,
    target: center,
    up: upForView(view),
    fovDegrees
  }, bounds);
}

export function boundsRadius(bounds: Bounds): number {
  return Math.hypot(bounds.size[0], bounds.size[1], bounds.size[2]) / 2;
}

function directionForView(view: StandardView): Vec3 {
  switch (view) {
    case "front":
      return [0, 0, 1];
    case "back":
      return [0, 0, -1];
    case "left":
      return [-1, 0, 0];
    case "right":
      return [1, 0, 0];
    case "top":
      return [0, 1, 0];
    case "bottom":
      return [0, -1, 0];
    case "iso":
      return normalize([1, 0.8, 1]);
  }
}

function upForView(view: StandardView): Vec3 {
  if (view === "top") {
    return [0, 0, -1];
  }
  if (view === "bottom") {
    return [0, 0, 1];
  }
  return DEFAULT_UP;
}

function normalize(v: Vec3): Vec3 {
  const length = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / length, v[1] / length, v[2] / length];
}

function distance(a: Vec3, b: Vec3): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}
