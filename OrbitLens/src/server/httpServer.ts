import http from "node:http";
import { OrbitLensService } from "../service/orbitLensService.js";
import { handleJsonRpc } from "./jsonRpc.js";
import type { JsonRpcRequest } from "../types.js";

export interface ServeOptions {
  port: number;
  host?: string;
  cwd?: string;
  outputDir?: string;
}

export async function serve(options: ServeOptions): Promise<http.Server> {
  const service = new OrbitLensService({
    cwd: options.cwd,
    outputDir: options.outputDir
  });

  const server = http.createServer(async (request, response) => {
    if (request.method !== "POST") {
      response.writeHead(405, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: "Use POST with a JSON-RPC request body." }));
      return;
    }

    try {
      const body = await readBody(request);
      const rpcRequest = JSON.parse(body) as JsonRpcRequest;
      const rpcResponse = await handleJsonRpc(service, rpcRequest);
      response.writeHead("error" in rpcResponse ? 400 : 200, { "content-type": "application/json" });
      response.end(JSON.stringify(rpcResponse, null, 2));
    } catch (error) {
      response.writeHead(400, { "content-type": "application/json" });
      response.end(JSON.stringify({
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32700,
          message: error instanceof Error ? error.message : String(error)
        }
      }));
    }
  });

  server.on("close", () => {
    void service.close();
  });

  await new Promise<void>((resolve) => {
    server.listen(options.port, options.host ?? "127.0.0.1", resolve);
  });
  return server;
}

async function readBody(request: http.IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf8");
}

