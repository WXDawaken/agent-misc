import { OrbitLensService } from "./service/orbitLensService.js";
import { serve } from "./server/httpServer.js";
import { handleJsonRpc } from "./server/jsonRpc.js";
import type { JsonRpcRequest } from "./types.js";

const [command, ...args] = process.argv.slice(2);

try {
  if (command === "serve") {
    const port = numberFlag(args, "--port", 3987);
    const server = await serve({ port, cwd: process.cwd() });
    const address = server.address();
    console.log(JSON.stringify({ ok: true, address }, null, 2));
  } else if (command === "call") {
    const method = stringFlag(args, "--method");
    const params = jsonFlag(args, "--params", {});
    const service = new OrbitLensService({ cwd: process.cwd() });
    try {
      const response = await handleJsonRpc(service, {
        jsonrpc: "2.0",
        id: 1,
        method,
        params
      } satisfies JsonRpcRequest);
      console.log(JSON.stringify(response, null, 2));
    } finally {
      await service.close();
    }
  } else if (command === "smoke") {
    const source = stringFlag(args, "--source", "fixtures/colored-cube.gltf");
    const service = new OrbitLensService({ cwd: process.cwd() });
    try {
      const load = await service.loadScene({ source });
      const pack = await service.observationPack({
        sceneId: load.sceneId,
        views: ["front", "right", "top", "iso"],
        options: {
          width: 360,
          height: 270,
          showGrid: true
        },
        contactSheet: true
      });
      console.log(JSON.stringify({
        load,
        summary: pack.summary,
        images: pack.images,
        contactSheetPath: pack.contactSheetPath,
        warnings: pack.warnings
      }, null, 2));
    } finally {
      await service.close();
    }
  } else {
    usage();
    process.exitCode = 1;
  }
} catch (error) {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exitCode = 1;
}

function usage(): void {
  console.log(`OrbitLens

Commands:
  orbitlens serve [--port 3987]
  orbitlens call --method <method> [--params <json>]
  orbitlens smoke [--source fixtures/colored-cube.gltf]
`);
}

function stringFlag(args: string[], name: string, fallback?: string): string {
  const index = args.indexOf(name);
  if (index === -1) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error(`Missing required flag ${name}`);
  }
  const value = args[index + 1];
  if (!value) {
    throw new Error(`Missing value for ${name}`);
  }
  return value;
}

function numberFlag(args: string[], name: string, fallback: number): number {
  const value = stringFlag(args, name, String(fallback));
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Expected a number for ${name}`);
  }
  return parsed;
}

function jsonFlag(args: string[], name: string, fallback: unknown): unknown {
  const index = args.indexOf(name);
  if (index === -1) {
    return fallback;
  }
  const value = args[index + 1];
  if (!value) {
    throw new Error(`Missing value for ${name}`);
  }
  return JSON.parse(value);
}

