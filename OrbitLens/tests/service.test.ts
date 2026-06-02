import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { existsSync, statSync } from "node:fs";
import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { cameraForStandardView } from "../src/camera/planner.js";
import { handleJsonRpc } from "../src/server/jsonRpc.js";
import { serve } from "../src/server/httpServer.js";
import { OrbitLensService } from "../src/service/orbitLensService.js";

const cwd = process.cwd();
const outputDir = path.join(cwd, ".orbitlens-test", "renders");
let service: OrbitLensService;

before(async () => {
  await rm(path.join(cwd, ".orbitlens-test"), { recursive: true, force: true });
  service = new OrbitLensService({ cwd, outputDir });
});

after(async () => {
  await service.close();
});

test("service loads a glTF fixture and returns scene summary metadata", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const summary = await service.sceneSummary({ sceneId: load.sceneId });

  assert.equal(load.rootObjectId, `${load.sceneId}:root`);
  assert.deepEqual(load.bounds.size, [1, 1, 1]);
  assert.equal(summary.triangleCount, 12);
  assert.equal(summary.objectCount, 2);
  assert.equal(summary.objects.some((object) => object.name === "ColoredCube"), true);
});

test("service also loads GLB assets", async () => {
  const glbPath = path.join(cwd, ".orbitlens-test", "fixtures", "colored-cube.glb");
  await writeColoredCubeGlb(glbPath);

  const load = await service.loadScene({ source: glbPath });
  const summary = await service.sceneSummary({ sceneId: load.sceneId });

  assert.deepEqual(load.bounds.size, [1, 1, 1]);
  assert.equal(summary.triangleCount, 12);
  assert.equal(summary.objects.some((object) => object.name === "ColoredCube"), true);
});

test("service renders explicit views and view grids as nonblank PNGs", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const camera = cameraForStandardView("iso", load.bounds);
  const image = await service.renderView({
    sceneId: load.sceneId,
    camera,
    options: {
      width: 256,
      height: 192,
      pass: "flat"
    }
  });

  assert.equal(image.width, 256);
  assert.equal(image.height, 192);
  assert.equal(image.pass, "flat");
  assert.equal(image.nonblank, true);
  assertFileExists(image.imagePath);

  const grid = await service.viewGrid({
    sceneId: load.sceneId,
    views: ["front", "right", "top"],
    options: {
      width: 180,
      height: 140,
      pass: "rgb"
    },
    contactSheet: true
  });

  assert.equal(grid.images.length, 3);
  assert.equal(grid.images.every((result) => result.nonblank), true);
  assert.ok(grid.contactSheetPath);
  assertFileExists(grid.contactSheetPath);
});

test("service renders all supported utility passes", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const camera = cameraForStandardView("iso", load.bounds);
  const passes = ["rgb", "flat", "wireframe", "mask", "depth", "normal"] as const;

  for (const pass of passes) {
    const image = await service.renderView({
      sceneId: load.sceneId,
      camera,
      options: {
        width: 180,
        height: 140,
        pass
      }
    });
    assert.equal(image.pass, pass);
    assert.equal(image.nonblank, true);
    assertFileExists(image.imagePath);
  }
});

test("JSON-RPC dispatcher exposes the observation_pack method", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const response = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "pack",
    method: "observation_pack",
    params: {
      sceneId: load.sceneId,
      views: ["front", "iso"],
      options: {
        width: 160,
        height: 120,
        pass: "wireframe"
      },
      contactSheet: true
    }
  });

  assert.equal(response.jsonrpc, "2.0");
  assert.equal(response.id, "pack");
  assert.ok("result" in response);
  const result = response.result as {
    summary: { triangleCount: number };
    images: Array<{ nonblank: boolean; pass: string }>;
    passes: string[];
    contactSheetPath?: string;
    contactSheets?: Array<{ pass: string; contactSheetPath: string }>;
  };
  assert.equal(result.summary.triangleCount, 12);
  assert.deepEqual(result.passes, ["wireframe"]);
  assert.equal(result.images.length, 2);
  assert.equal(result.images.every((image) => image.nonblank && image.pass === "wireframe"), true);
  assert.ok(result.contactSheetPath);
  assertFileExists(result.contactSheetPath);
  assert.ok(result.contactSheets);
  assert.equal(result.contactSheets.length, 1);
  assert.equal(result.contactSheets[0].pass, "wireframe");
  assert.equal(result.contactSheets[0].contactSheetPath, result.contactSheetPath);
});

test("JSON-RPC observation_pack supports multiple passes", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const response = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "multi-pass-pack",
    method: "observation_pack",
    params: {
      sceneId: load.sceneId,
      views: ["front", "iso"],
      passes: ["rgb", "depth", "normal"],
      options: {
        width: 160,
        height: 120
      },
      contactSheet: true
    }
  });

  assert.equal(response.jsonrpc, "2.0");
  assert.equal(response.id, "multi-pass-pack");
  assert.ok("result" in response);
  const result = response.result as {
    passes: string[];
    images: Array<{ nonblank: boolean; pass: string; imagePath: string }>;
    contactSheetPath?: string;
    contactSheets?: Array<{ pass: string; contactSheetPath: string }>;
  };

  assert.deepEqual(result.passes, ["rgb", "depth", "normal"]);
  assert.equal(result.images.length, 6);
  assert.equal(result.images.every((image) => image.nonblank), true);
  assert.deepEqual(
    result.images.map((image) => image.pass),
    ["rgb", "rgb", "depth", "depth", "normal", "normal"]
  );
  assert.ok(result.contactSheets);
  assert.equal(result.contactSheets.length, 3);
  assert.deepEqual(result.contactSheets.map((sheet) => sheet.pass), ["rgb", "depth", "normal"]);
  assert.equal(result.contactSheetPath, result.contactSheets[0].contactSheetPath);
  for (const image of result.images) {
    assertFileExists(image.imagePath);
  }
  for (const sheet of result.contactSheets) {
    assertFileExists(sheet.contactSheetPath);
  }
});

test("service measures point and object distances", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const objectId = `${load.sceneId}:object:0`;

  const pointDistance = await service.measure({
    sceneId: load.sceneId,
    mode: "point",
    a: { point: [0, 0, 0] },
    b: { point: [3, 4, 12] }
  });
  assert.equal(pointDistance.distance, 13);
  assert.deepEqual(pointDistance.a, [0, 0, 0]);
  assert.deepEqual(pointDistance.b, [3, 4, 12]);

  const centerDistance = await service.measure({
    sceneId: load.sceneId,
    a: { objectId },
    b: { point: [1, 0, 0] }
  });
  assert.equal(centerDistance.distance, 1);
  assert.deepEqual(centerDistance.a, [0, 0, 0]);

  const closestBoundsDistance = await service.measure({
    sceneId: load.sceneId,
    mode: "closest_bounds",
    a: { point: [2, 0, 0] },
    b: { objectId }
  });
  assert.equal(closestBoundsDistance.distance, 1.5);
  assert.deepEqual(closestBoundsDistance.b, [0.5, 0, 0]);
});

test("JSON-RPC dispatcher exposes measure", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const response = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "measure",
    method: "measure",
    params: {
      sceneId: load.sceneId,
      mode: "point",
      a: { point: [0, 0, 0] },
      b: { point: [0, 6, 8] }
    }
  });

  assert.ok("result" in response);
  const result = response.result as { distance: number; units?: string };
  assert.equal(result.distance, 10);
  assert.equal(result.units, "scene");
});

test("service picks a 3D point from image pixels", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const camera = cameraForStandardView("front", load.bounds);
  const pick = await service.pick({
    sceneId: load.sceneId,
    camera,
    imageX: 128,
    imageY: 96,
    width: 256,
    height: 192
  });

  assert.equal(pick.hit, true);
  assert.equal(pick.objectId, `${load.sceneId}:object:0`);
  assert.ok(pick.point);
  assert.ok(Math.abs(pick.point[0]) < 1e-6);
  assert.ok(Math.abs(pick.point[1]) < 1e-6);
  assert.ok(Math.abs(pick.point[2] - 0.5) < 1e-6);
  assert.ok(pick.distance && pick.distance > 0);
});

test("JSON-RPC dispatcher exposes pick", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const camera = cameraForStandardView("front", load.bounds);
  const response = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "pick",
    method: "pick",
    params: {
      sceneId: load.sceneId,
      camera,
      imageX: 80,
      imageY: 60,
      width: 160,
      height: 120
    }
  });

  assert.ok("result" in response);
  const result = response.result as { hit: boolean; objectId?: string };
  assert.equal(result.hit, true);
  assert.equal(result.objectId, `${load.sceneId}:object:0`);
});

test("JSON-RPC pick result can be measured from the camera", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const camera = cameraForStandardView("front", load.bounds);
  const pickResponse = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "pick-for-measure",
    method: "pick",
    params: {
      sceneId: load.sceneId,
      camera,
      imageX: 128,
      imageY: 96,
      width: 256,
      height: 192
    }
  });

  assert.ok("result" in pickResponse);
  const pick = pickResponse.result as {
    hit: boolean;
    point?: [number, number, number];
    distance?: number;
  };
  assert.equal(pick.hit, true);
  assert.ok(pick.point);
  assert.ok(pick.distance);

  const measureResponse = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "measure-picked-point",
    method: "measure",
    params: {
      sceneId: load.sceneId,
      mode: "point",
      a: { point: camera.position },
      b: { point: pick.point }
    }
  });

  assert.ok("result" in measureResponse);
  const measure = measureResponse.result as { distance: number };
  assert.ok(Math.abs(measure.distance - pick.distance) < 1e-9);
});

test("set_visibility hides and restores objects for render and pick", async () => {
  const load = await service.loadScene({ source: "fixtures/colored-cube.gltf" });
  const objectId = `${load.sceneId}:object:0`;
  const camera = cameraForStandardView("front", load.bounds);

  const hideResponse = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "hide",
    method: "set_visibility",
    params: {
      sceneId: load.sceneId,
      objectId,
      visible: false
    }
  });
  assert.ok("result" in hideResponse);
  const hide = hideResponse.result as { visible: boolean; changedObjectIds: string[] };
  assert.equal(hide.visible, false);
  assert.deepEqual(hide.changedObjectIds, [objectId]);

  const hiddenSummary = await service.sceneSummary({ sceneId: load.sceneId });
  assert.equal(hiddenSummary.objects.find((object) => object.id === objectId)?.visible, false);

  const hiddenImage = await service.renderView({
    sceneId: load.sceneId,
    camera,
    options: {
      width: 128,
      height: 96
    }
  });
  assert.deepEqual(hiddenImage.visibleObjects, []);

  const hiddenPick = await service.pick({
    sceneId: load.sceneId,
    camera,
    imageX: 64,
    imageY: 48,
    width: 128,
    height: 96
  });
  assert.equal(hiddenPick.hit, false);

  const showResponse = await handleJsonRpc(service, {
    jsonrpc: "2.0",
    id: "show",
    method: "set_visibility",
    params: {
      sceneId: load.sceneId,
      objectId,
      visible: true
    }
  });
  assert.ok("result" in showResponse);
  const show = showResponse.result as { visible: boolean; changedObjectIds: string[] };
  assert.equal(show.visible, true);
  assert.deepEqual(show.changedObjectIds, [objectId]);

  const restoredPick = await service.pick({
    sceneId: load.sceneId,
    camera,
    imageX: 64,
    imageY: 48,
    width: 128,
    height: 96
  });
  assert.equal(restoredPick.hit, true);
  assert.equal(restoredPick.objectId, objectId);
});

test("HTTP JSON-RPC server accepts local service requests", async () => {
  const server = await serve({
    port: 0,
    cwd,
    outputDir: path.join(cwd, ".orbitlens-test", "http-renders")
  });

  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const endpoint = `http://127.0.0.1:${address.port}`;
    const load = await postRpc(endpoint, {
      jsonrpc: "2.0",
      id: 1,
      method: "load_scene",
      params: { source: "fixtures/colored-cube.gltf" }
    });
    assert.ok("result" in load);
    const sceneId = (load.result as { sceneId: string }).sceneId;

    const pack = await postRpc(endpoint, {
      jsonrpc: "2.0",
      id: 2,
      method: "observation_pack",
      params: {
        sceneId,
        views: ["iso"],
        options: {
          width: 120,
          height: 90
        },
        contactSheet: true
      }
    });
    assert.ok("result" in pack);
    const result = pack.result as { images: Array<{ nonblank: boolean }>; contactSheetPath?: string };
    assert.equal(result.images.length, 1);
    assert.equal(result.images[0].nonblank, true);
    assert.ok(result.contactSheetPath);
    assertFileExists(result.contactSheetPath);
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => {
        if (error) {
          reject(error);
        } else {
          resolve();
        }
      });
    });
  }
});

function assertFileExists(filePath: string): void {
  assert.equal(existsSync(filePath), true, `${filePath} should exist`);
  assert.ok(statSync(filePath).size > 0, `${filePath} should not be empty`);
}

async function postRpc(endpoint: string, body: unknown): Promise<Record<string, unknown>> {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    assert.fail(await response.text());
  }
  return response.json() as Promise<Record<string, unknown>>;
}

async function writeColoredCubeGlb(filePath: string): Promise<void> {
  const positions = [
    -0.5, -0.5, 0.5, 0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, 0.5, 0.5,
    0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5,
    -0.5, -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5, -0.5,
    0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5, 0.5, -0.5, 0.5, 0.5, 0.5,
    -0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, -0.5, -0.5, 0.5, -0.5,
    -0.5, -0.5, -0.5, 0.5, -0.5, -0.5, 0.5, -0.5, 0.5, -0.5, -0.5, 0.5
  ];
  const faceColors = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 0],
    [1, 0, 1],
    [0, 1, 1]
  ];
  const colors = faceColors.flatMap((color) => [...color, ...color, ...color, ...color]);
  const indices: number[] = [];
  for (let face = 0; face < 6; face += 1) {
    const offset = face * 4;
    indices.push(offset, offset + 1, offset + 2, offset, offset + 2, offset + 3);
  }

  const positionBuffer = floatBuffer(positions);
  const colorBuffer = floatBuffer(colors);
  const indexBuffer = uint16Buffer(indices);
  const binary = Buffer.concat([positionBuffer, colorBuffer, indexBuffer]);
  const json = Buffer.from(JSON.stringify({
    asset: { version: "2.0", generator: "OrbitLens GLB test fixture" },
    scene: 0,
    scenes: [{ name: "Colored Cube Scene", nodes: [0] }],
    nodes: [{ name: "ColoredCube", mesh: 0 }],
    meshes: [{
      name: "ColoredCubeMesh",
      primitives: [{ attributes: { POSITION: 0, COLOR_0: 1 }, indices: 2, material: 0 }]
    }],
    materials: [{
      name: "VertexColorMat",
      pbrMetallicRoughness: { baseColorFactor: [1, 1, 1, 1], metallicFactor: 0, roughnessFactor: 0.7 },
      doubleSided: true
    }],
    accessors: [
      { bufferView: 0, componentType: 5126, count: 24, type: "VEC3", min: [-0.5, -0.5, -0.5], max: [0.5, 0.5, 0.5] },
      { bufferView: 1, componentType: 5126, count: 24, type: "VEC3", min: [0, 0, 0], max: [1, 1, 1] },
      { bufferView: 2, componentType: 5123, count: 36, type: "SCALAR", min: [0], max: [23] }
    ],
    bufferViews: [
      { buffer: 0, byteOffset: 0, byteLength: positionBuffer.length, target: 34962 },
      { buffer: 0, byteOffset: positionBuffer.length, byteLength: colorBuffer.length, target: 34962 },
      { buffer: 0, byteOffset: positionBuffer.length + colorBuffer.length, byteLength: indexBuffer.length, target: 34963 }
    ],
    buffers: [{ byteLength: binary.length }]
  }), "utf8");

  const jsonChunk = pad(json, 0x20);
  const binaryChunk = pad(binary, 0);
  const header = Buffer.alloc(12);
  header.writeUInt32LE(0x46546c67, 0);
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(12 + 8 + jsonChunk.length + 8 + binaryChunk.length, 8);
  const jsonHeader = chunkHeader(jsonChunk.length, 0x4e4f534a);
  const binaryHeader = chunkHeader(binaryChunk.length, 0x004e4942);

  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, Buffer.concat([header, jsonHeader, jsonChunk, binaryHeader, binaryChunk]));
}

function floatBuffer(values: number[]): Buffer {
  const buffer = Buffer.alloc(values.length * 4);
  values.forEach((value, index) => buffer.writeFloatLE(value, index * 4));
  return buffer;
}

function uint16Buffer(values: number[]): Buffer {
  const buffer = Buffer.alloc(values.length * 2);
  values.forEach((value, index) => buffer.writeUInt16LE(value, index * 2));
  return buffer;
}

function pad(buffer: Buffer, fill: number): Buffer {
  const padding = (4 - (buffer.length % 4)) % 4;
  return padding === 0 ? buffer : Buffer.concat([buffer, Buffer.alloc(padding, fill)]);
}

function chunkHeader(length: number, type: number): Buffer {
  const header = Buffer.alloc(8);
  header.writeUInt32LE(length, 0);
  header.writeUInt32LE(type, 4);
  return header;
}
