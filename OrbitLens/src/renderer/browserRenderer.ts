import { readFile } from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium, type Browser, type Page } from "playwright";
import type {
  Bounds,
  LoadSceneResponse,
  RenderPass,
  ResolvedCameraSpec,
  SceneId,
  SceneSummaryResponse,
  PickResponse,
  SetVisibilityRequest,
  SetVisibilityResponse
} from "../types.js";
import { resolveFromRoot } from "../util/paths.js";

export interface BrowserSceneSource {
  sceneId: SceneId;
  name: string;
  format: "gltf" | "glb";
  baseUrl: string;
  text?: string;
  base64?: string;
}

export interface BrowserRenderRequest {
  sceneId: SceneId;
  camera: ResolvedCameraSpec;
  width: number;
  height: number;
  pass: RenderPass;
  transparentBackground: boolean;
  showGrid: boolean;
  showAxes: boolean;
}

export interface BrowserRenderResponse {
  dataUrl: string;
  width: number;
  height: number;
  camera: ResolvedCameraSpec;
  pass: RenderPass;
  visibleObjects: string[];
  warnings: string[];
}

export interface BrowserPickRequest {
  sceneId: SceneId;
  camera: ResolvedCameraSpec;
  imageX: number;
  imageY: number;
  width: number;
  height: number;
}

export class BrowserRenderer {
  private browser?: Browser;
  private page?: Page;
  private staticServer?: http.Server;
  private staticBaseUrl?: string;

  async loadScene(source: BrowserSceneSource): Promise<LoadSceneResponse> {
    const page = await this.ensurePage();
    return page.evaluate(async (payload) => globalThis.orbitLens.loadScene(payload), source);
  }

  async sceneSummary(sceneId: SceneId): Promise<SceneSummaryResponse> {
    const page = await this.ensurePage();
    return page.evaluate(async (payload) => globalThis.orbitLens.sceneSummary(payload), { sceneId });
  }

  async renderView(request: BrowserRenderRequest): Promise<BrowserRenderResponse> {
    const page = await this.ensurePage();
    return page.evaluate(async (payload) => globalThis.orbitLens.renderView(payload), request);
  }

  async pick(request: BrowserPickRequest): Promise<PickResponse> {
    const page = await this.ensurePage();
    return page.evaluate(async (payload) => globalThis.orbitLens.pick(payload), request);
  }

  async setVisibility(request: SetVisibilityRequest): Promise<SetVisibilityResponse> {
    const page = await this.ensurePage();
    return page.evaluate(async (payload) => globalThis.orbitLens.setVisibility(payload), request);
  }

  async sceneBounds(sceneId: SceneId): Promise<Bounds> {
    const summary = await this.sceneSummary(sceneId);
    return summary.bounds;
  }

  async close(): Promise<void> {
    await this.browser?.close();
    await closeServer(this.staticServer);
    this.browser = undefined;
    this.page = undefined;
    this.staticServer = undefined;
    this.staticBaseUrl = undefined;
  }

  private async ensurePage(): Promise<Page> {
    if (this.page) {
      return this.page;
    }

    this.browser = await launchChromium();
    this.page = await this.browser.newPage({
      viewport: { width: 960, height: 720 },
      deviceScaleFactor: 1
    });
    const pageMessages: string[] = [];
    this.page.on("console", (message) => {
      if (["error", "warning"].includes(message.type())) {
        pageMessages.push(`${message.type()}: ${message.text()}`);
      }
    });
    this.page.on("pageerror", (error) => {
      pageMessages.push(`pageerror: ${error.message}`);
    });
    const rendererUrl = `${await this.ensureStaticServer()}/src/renderer/renderer.html`;
    await this.page.goto(rendererUrl);
    try {
      await this.page.waitForFunction(() => Boolean(globalThis.orbitLens), undefined, { timeout: 10000 });
    } catch (error) {
      throw new Error(`OrbitLens renderer did not initialize. ${pageMessages.join(" | ") || String(error)}`);
    }
    return this.page;
  }

  private async ensureStaticServer(): Promise<string> {
    if (this.staticBaseUrl) {
      return this.staticBaseUrl;
    }

    const root = resolveFromRoot(".");
    this.staticServer = http.createServer(async (request, response) => {
      try {
        const url = new URL(request.url ?? "/", "http://127.0.0.1");
        const decoded = decodeURIComponent(url.pathname.replace(/^\/+/u, ""));
        const filePath = path.resolve(root, decoded || "src/renderer/renderer.html");
        if (!filePath.startsWith(root)) {
          response.writeHead(403);
          response.end("Forbidden");
          return;
        }
        const body = await readFile(filePath);
        response.writeHead(200, { "content-type": contentType(filePath) });
        response.end(body);
      } catch (error) {
        response.writeHead(404, { "content-type": "text/plain" });
        response.end(error instanceof Error ? error.message : String(error));
      }
    });

    await new Promise<void>((resolve) => {
      this.staticServer?.listen(0, "127.0.0.1", resolve);
    });
    const address = this.staticServer.address();
    if (!address || typeof address === "string") {
      throw new Error("Failed to start OrbitLens renderer static server");
    }
    this.staticBaseUrl = `http://127.0.0.1:${address.port}`;
    return this.staticBaseUrl;
  }
}

async function launchChromium(): Promise<Browser> {
  const channel = process.env.ORBITLENS_BROWSER_CHANNEL;
  const launchOptions = {
    headless: process.env.ORBITLENS_HEADLESS !== "0",
    args: ["--use-angle=swiftshader", "--use-gl=angle"]
  };

  if (channel) {
    return chromium.launch({ ...launchOptions, channel });
  }

  const candidateChannels = process.platform === "win32" ? ["msedge", "chrome"] : ["chrome", "chromium"];
  for (const candidate of candidateChannels) {
    try {
      return await chromium.launch({ ...launchOptions, channel: candidate });
    } catch {
      // Try the next installed Chromium-family browser before falling back.
    }
  }

  return chromium.launch(launchOptions);
}

export async function readSceneSource(sceneId: SceneId, sourcePath: string, format: "gltf" | "glb"): Promise<BrowserSceneSource> {
  const absolutePath = path.resolve(sourcePath);
  const baseUrl = pathToFileURL(path.dirname(absolutePath) + path.sep).href;
  const name = path.basename(absolutePath);

  if (format === "gltf") {
    return {
      sceneId,
      name,
      format,
      baseUrl,
      text: await readFile(absolutePath, "utf8")
    };
  }

  const bytes = await readFile(absolutePath);
  return {
    sceneId,
    name,
    format,
    baseUrl,
    base64: bytes.toString("base64")
  };
}

function contentType(filePath: string): string {
  switch (path.extname(filePath).toLowerCase()) {
    case ".html":
      return "text/html; charset=utf-8";
    case ".js":
      return "text/javascript; charset=utf-8";
    case ".json":
      return "application/json; charset=utf-8";
    case ".css":
      return "text/css; charset=utf-8";
    case ".wasm":
      return "application/wasm";
    default:
      return "application/octet-stream";
  }
}

async function closeServer(server: http.Server | undefined): Promise<void> {
  if (!server) {
    return;
  }
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

declare global {
  // eslint-disable-next-line no-var
  var orbitLens: {
    loadScene(source: BrowserSceneSource): Promise<LoadSceneResponse>;
    sceneSummary(request: { sceneId: SceneId }): Promise<SceneSummaryResponse>;
    renderView(request: BrowserRenderRequest): Promise<BrowserRenderResponse>;
    pick(request: BrowserPickRequest): Promise<PickResponse>;
    setVisibility(request: SetVisibilityRequest): Promise<SetVisibilityResponse>;
  };
}
