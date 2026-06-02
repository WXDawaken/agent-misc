import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { BrowserRenderer, readSceneSource } from "../renderer/browserRenderer.js";
import { cameraForStandardView, DEFAULT_DISTANCE_SCALE, resolveCamera } from "../camera/planner.js";
import type {
  ImageResult,
  LoadSceneRequest,
  LoadSceneResponse,
  MeasureEndpoint,
  MeasureRequest,
  MeasureResponse,
  ObservationPackContactSheet,
  ObservationPackRequest,
  ObservationPackResponse,
  PickRequest,
  PickResponse,
  RenderOptions,
  RenderPass,
  RenderViewRequest,
  SceneId,
  SceneSummaryRequest,
  SceneSummaryResponse,
  SetVisibilityRequest,
  SetVisibilityResponse,
  StandardView,
  ViewGridRequest,
  ViewGridResponse
} from "../types.js";
import { resolveFromRoot } from "../util/paths.js";
import { writeContactSheet, writePngFromDataUrl } from "../util/images.js";

interface SceneRecord {
  sceneId: SceneId;
  source: string;
  load: LoadSceneResponse;
}

export interface OrbitLensServiceOptions {
  cwd?: string;
  outputDir?: string;
  renderer?: BrowserRenderer;
}

export class OrbitLensService {
  private readonly cwd: string;
  private readonly defaultOutputDir: string;
  private readonly renderer: BrowserRenderer;
  private readonly scenes = new Map<SceneId, SceneRecord>();
  private renderCounter = 0;

  constructor(options: OrbitLensServiceOptions = {}) {
    this.cwd = options.cwd ?? process.cwd();
    this.defaultOutputDir = options.outputDir ?? resolveFromRoot(".orbitlens", "renders");
    this.renderer = options.renderer ?? new BrowserRenderer();
  }

  async loadScene(request: LoadSceneRequest): Promise<LoadSceneResponse> {
    const sourcePath = this.resolveSourcePath(request.source);
    const format = detectFormat(sourcePath, request.formatHint);
    const sceneId = `scene-${randomUUID()}`;
    const source = await readSceneSource(sceneId, sourcePath, format);
    const response = await this.renderer.loadScene(source);
    this.scenes.set(sceneId, {
      sceneId,
      source: sourcePath,
      load: response
    });
    return response;
  }

  async sceneSummary(request: SceneSummaryRequest): Promise<SceneSummaryResponse> {
    this.requireScene(request.sceneId);
    return this.renderer.sceneSummary(request.sceneId);
  }

  async renderView(request: RenderViewRequest): Promise<ImageResult> {
    const scene = this.requireScene(request.sceneId);
    const options = this.normalizeRenderOptions(request.options);
    const camera = resolveCamera(request.camera, scene.load.bounds);
    const rendered = await this.renderer.renderView({
      sceneId: request.sceneId,
      camera,
      width: options.width,
      height: options.height,
      pass: options.pass,
      transparentBackground: options.transparentBackground,
      showGrid: options.showGrid,
      showAxes: options.showAxes
    });
    const imagePath = this.nextImagePath(request.sceneId, options.pass, options.outputDir);
    const { nonblank } = await writePngFromDataUrl(rendered.dataUrl, imagePath);
    const warnings = [...rendered.warnings];
    if (!nonblank) {
      warnings.push("Rendered image appears blank or single-color.");
    }

    return {
      imagePath,
      width: rendered.width,
      height: rendered.height,
      camera: rendered.camera,
      pass: rendered.pass,
      visibleObjects: rendered.visibleObjects,
      nonblank,
      warnings
    };
  }

  async viewGrid(request: ViewGridRequest): Promise<ViewGridResponse> {
    const scene = this.requireScene(request.sceneId);
    const views = request.views ?? DEFAULT_GRID_VIEWS;
    const options = this.normalizeRenderOptions(request.options);
    const bounds = request.targetObjectId
      ? await this.boundsForObject(request.sceneId, request.targetObjectId)
      : scene.load.bounds;
    const images: ImageResult[] = [];
    const warnings: string[] = [];

    for (const view of views) {
      const camera = cameraForStandardView(view, bounds, request.distanceScale ?? DEFAULT_DISTANCE_SCALE);
      const image = await this.renderView({
        sceneId: request.sceneId,
        camera,
        options: {
          ...options,
          outputDir: options.outputDir
        }
      });
      images.push(image);
      warnings.push(...image.warnings.map((warning) => `${view}: ${warning}`));
    }

    let contactSheetPath: string | undefined;
    if (request.contactSheet ?? true) {
      contactSheetPath = path.join(options.outputDir, `${request.sceneId}-view-grid.png`);
      await writeContactSheet(images.map((image) => image.imagePath), contactSheetPath, Math.min(3, images.length));
    }

    return {
      images,
      contactSheetPath,
      warnings
    };
  }

  async observationPack(request: ObservationPackRequest): Promise<ObservationPackResponse> {
    const summary = request.includeSummary === false ? undefined : await this.sceneSummary({ sceneId: request.sceneId });
    const passes = normalizeObservationPasses(request);

    if (passes.length === 1) {
      const pass = passes[0];
      const grid = await this.viewGrid({
        ...request,
        options: {
          ...(request.options ?? {}),
          pass
        }
      });
      const contactSheets = grid.contactSheetPath
        ? [{ pass, contactSheetPath: grid.contactSheetPath }]
        : undefined;
      return {
        sceneId: request.sceneId,
        summary,
        passes,
        images: grid.images,
        contactSheetPath: grid.contactSheetPath,
        contactSheets,
        warnings: grid.warnings
      };
    }

    const baseOptions = this.normalizeRenderOptions(request.options);
    const images: ImageResult[] = [];
    const warnings: string[] = [];
    const contactSheets: ObservationPackContactSheet[] = [];

    for (const pass of passes) {
      const grid = await this.viewGrid({
        ...request,
        options: {
          ...(request.options ?? {}),
          pass,
          outputDir: path.join(baseOptions.outputDir, pass)
        }
      });

      images.push(...grid.images);
      warnings.push(...grid.warnings.map((warning) => `${pass}: ${warning}`));
      if (grid.contactSheetPath) {
        contactSheets.push({ pass, contactSheetPath: grid.contactSheetPath });
      }
    }

    return {
      sceneId: request.sceneId,
      summary,
      passes,
      images,
      contactSheetPath: contactSheets[0]?.contactSheetPath,
      contactSheets: contactSheets.length > 0 ? contactSheets : undefined,
      warnings
    };
  }

  async measure(request: MeasureRequest): Promise<MeasureResponse> {
    this.requireScene(request.sceneId);
    const mode = request.mode ?? "center";
    const summary = await this.sceneSummary({ sceneId: request.sceneId });
    const a = resolveMeasureEndpoint(request.a, request.b, summary, mode);
    const b = resolveMeasureEndpoint(request.b, request.a, summary, mode);
    const distance = vecDistance(a, b);

    return {
      distance,
      units: "scene",
      a,
      b,
      mode,
      warnings: []
    };
  }

  async pick(request: PickRequest): Promise<PickResponse> {
    const scene = this.requireScene(request.sceneId);
    const camera = resolveCamera(request.camera, scene.load.bounds);
    return this.renderer.pick({
      sceneId: request.sceneId,
      camera,
      imageX: request.imageX,
      imageY: request.imageY,
      width: request.width,
      height: request.height
    });
  }

  async setVisibility(request: SetVisibilityRequest): Promise<SetVisibilityResponse> {
    this.requireScene(request.sceneId);
    return this.renderer.setVisibility({
      ...request,
      recursive: request.recursive ?? true
    });
  }

  async close(): Promise<void> {
    await this.renderer.close();
  }

  private resolveSourcePath(source: string): string {
    if (source.startsWith("file://")) {
      return fileURLToPath(source);
    }
    return path.isAbsolute(source) ? source : path.resolve(this.cwd, source);
  }

  private requireScene(sceneId: SceneId): SceneRecord {
    const scene = this.scenes.get(sceneId);
    if (!scene) {
      throw new Error(`Unknown sceneId: ${sceneId}`);
    }
    return scene;
  }

  private async boundsForObject(sceneId: SceneId, objectId: string) {
    const summary = await this.sceneSummary({ sceneId });
    const object = summary.objects.find((candidate) => candidate.id === objectId);
    if (!object?.bounds) {
      throw new Error(`Object has no renderable bounds: ${objectId}`);
    }
    return object.bounds;
  }

  private nextImagePath(sceneId: SceneId, pass: RenderPass, outputDir: string): string {
    this.renderCounter += 1;
    return path.join(outputDir, `${sceneId}-${String(this.renderCounter).padStart(4, "0")}-${pass}.png`);
  }

  private normalizeRenderOptions(options: RenderOptions = {}): NormalizedRenderOptions {
    return {
      width: options.width ?? 800,
      height: options.height ?? 600,
      pass: options.pass ?? "rgb",
      transparentBackground: options.transparentBackground ?? false,
      showGrid: options.showGrid ?? false,
      showAxes: options.showAxes ?? false,
      outputDir: path.resolve(options.outputDir ?? this.defaultOutputDir)
    };
  }
}

const DEFAULT_GRID_VIEWS: StandardView[] = ["front", "back", "left", "right", "top", "iso"];
const SUPPORTED_RENDER_PASSES = new Set<RenderPass>(["rgb", "wireframe", "flat", "mask", "depth", "normal"]);

interface NormalizedRenderOptions {
  width: number;
  height: number;
  pass: RenderPass;
  transparentBackground: boolean;
  showGrid: boolean;
  showAxes: boolean;
  outputDir: string;
}

function detectFormat(sourcePath: string, hint: LoadSceneRequest["formatHint"]): "gltf" | "glb" {
  if (hint && hint !== "auto") {
    return hint;
  }
  const extension = path.extname(sourcePath).toLowerCase();
  if (extension === ".gltf") {
    return "gltf";
  }
  if (extension === ".glb") {
    return "glb";
  }
  throw new Error(`Unsupported scene format for ${sourcePath}; expected .gltf or .glb`);
}

function normalizeObservationPasses(request: ObservationPackRequest): RenderPass[] {
  const requested: RenderPass[] = request.passes?.length ? request.passes : [request.options?.pass ?? "rgb"];
  const passes: RenderPass[] = [];
  const seen = new Set<RenderPass>();

  for (const pass of requested) {
    if (!SUPPORTED_RENDER_PASSES.has(pass)) {
      throw new Error(`Unsupported render pass for observation_pack: ${pass}`);
    }
    if (!seen.has(pass)) {
      seen.add(pass);
      passes.push(pass);
    }
  }

  return passes;
}

function resolveMeasureEndpoint(
  endpoint: MeasureEndpoint,
  otherEndpoint: MeasureEndpoint,
  summary: SceneSummaryResponse,
  mode: MeasureRequest["mode"]
) {
  if (endpoint.point) {
    return endpoint.point;
  }

  if (mode === "point") {
    throw new Error("Measure mode 'point' requires explicit point endpoints");
  }

  if (!endpoint.objectId) {
    throw new Error("Measure endpoint must include either point or objectId");
  }

  const object = summary.objects.find((candidate) => candidate.id === endpoint.objectId);
  if (!object) {
    throw new Error(`Unknown objectId: ${endpoint.objectId}`);
  }
  if (!object.bounds) {
    throw new Error(`Object has no measurable bounds: ${endpoint.objectId}`);
  }

  if (mode === "closest_bounds") {
    return closestPointOnBounds(object.bounds, referencePointForEndpoint(otherEndpoint, summary));
  }

  return object.bounds.center;
}

function referencePointForEndpoint(endpoint: MeasureEndpoint, summary: SceneSummaryResponse): [number, number, number] {
  if (endpoint.point) {
    return endpoint.point;
  }
  if (endpoint.objectId) {
    const object = summary.objects.find((candidate) => candidate.id === endpoint.objectId);
    if (object?.bounds) {
      return object.bounds.center;
    }
  }
  return summary.bounds.center;
}

function closestPointOnBounds(bounds: { min: number[]; max: number[] }, reference: [number, number, number]) {
  return [
    clamp(reference[0], bounds.min[0], bounds.max[0]),
    clamp(reference[1], bounds.min[1], bounds.max[1]),
    clamp(reference[2], bounds.min[2], bounds.max[2])
  ] as [number, number, number];
}

function vecDistance(a: [number, number, number], b: [number, number, number]): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
