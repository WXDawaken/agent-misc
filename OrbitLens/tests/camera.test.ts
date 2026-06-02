import assert from "node:assert/strict";
import { test } from "node:test";
import { cameraForStandardView, DEFAULT_DISTANCE_SCALE, resolveCamera } from "../src/camera/planner.js";
import type { Bounds } from "../src/types.js";

const cubeBounds: Bounds = {
  min: [-0.5, -0.5, -0.5],
  max: [0.5, 0.5, 0.5],
  center: [0, 0, 0],
  size: [1, 1, 1]
};

const avocadoLikeBounds: Bounds = {
  min: [-0.02128091, -0.00004773855, -0.0138090011],
  max: [0.02128091, 0.06284806, 0.013809],
  center: [0, 0.031400160725, -5.499999995370319e-10],
  size: [0.04256182, 0.06289579854999999, 0.027618001099999998]
};

test("cameraForStandardView frames the scene from canonical directions", () => {
  const front = cameraForStandardView("front", cubeBounds);
  const right = cameraForStandardView("right", cubeBounds);
  const top = cameraForStandardView("top", cubeBounds);

  assert.equal(front.target[0], 0);
  assert.equal(front.target[1], 0);
  assert.equal(front.target[2], 0);
  assert.equal(front.position[0], 0);
  assert.equal(front.position[1], 0);
  assert.ok(front.position[2] > 1);

  assert.ok(right.position[0] > 1);
  assert.equal(right.position[1], 0);
  assert.equal(right.position[2], 0);

  assert.ok(top.position[1] > 1);
  assert.deepEqual(top.up, [0, 0, -1]);
});

test("resolveCamera fills defaults from scene bounds", () => {
  const camera = resolveCamera({
    position: [2, 2, 2],
    target: [0, 0, 0]
  }, cubeBounds);

  assert.deepEqual(camera.up, [0, 1, 0]);
  assert.equal(camera.fovDegrees, 45);
  assert.ok(camera.near > 0);
  assert.ok(camera.far > camera.near);
});

test("cameraForStandardView fits tiny models without a one-unit radius floor", () => {
  const front = cameraForStandardView("front", avocadoLikeBounds);
  const sceneRadius = Math.hypot(...avocadoLikeBounds.size) / 2;
  const expectedDistance = sceneRadius / Math.sin((45 * Math.PI / 180) / 2) * DEFAULT_DISTANCE_SCALE;
  const actualDistance = front.position[2] - front.target[2];

  assert.ok(actualDistance < 0.2);
  assert.ok(Math.abs(actualDistance - expectedDistance) < 1e-12);
  assert.ok(front.near < actualDistance);
  assert.ok(front.far > actualDistance + sceneRadius);
});
