import type { JsonRpcFailure, JsonRpcRequest, JsonRpcResponse, JsonRpcSuccess } from "../types.js";
import type {
  LoadSceneRequest,
  MeasureRequest,
  ObservationPackRequest,
  PickRequest,
  RenderViewRequest,
  SceneSummaryRequest,
  SetVisibilityRequest,
  ViewGridRequest
} from "../types.js";
import type { OrbitLensService } from "../service/orbitLensService.js";

export async function handleJsonRpc(service: OrbitLensService, request: JsonRpcRequest): Promise<JsonRpcResponse> {
  const id = request.id ?? null;

  try {
    if (request.jsonrpc !== "2.0") {
      return failure(id, -32600, "Invalid JSON-RPC version");
    }

    const result = await dispatch(service, request.method, request.params);
    return success(id, result);
  } catch (error) {
    return failure(id, -32000, error instanceof Error ? error.message : String(error));
  }
}

async function dispatch(service: OrbitLensService, method: string, params: unknown): Promise<unknown> {
  switch (method) {
    case "load_scene":
      return service.loadScene(asRecord<LoadSceneRequest>(params));
    case "scene_summary":
      return service.sceneSummary(asRecord<SceneSummaryRequest>(params));
    case "render_view":
      return service.renderView(asRecord<RenderViewRequest>(params));
    case "view_grid":
      return service.viewGrid(asRecord<ViewGridRequest>(params));
    case "observation_pack":
      return service.observationPack(asRecord<ObservationPackRequest>(params));
    case "measure":
      return service.measure(asRecord<MeasureRequest>(params));
    case "pick":
      return service.pick(asRecord<PickRequest>(params));
    case "set_visibility":
      return service.setVisibility(asRecord<SetVisibilityRequest>(params));
    default:
      throw new Error(`Unknown method: ${method}`);
  }
}

function asRecord<T>(params: unknown): T {
  if (!params || typeof params !== "object" || Array.isArray(params)) {
    throw new Error("JSON-RPC params must be an object");
  }
  return params as T;
}

function success(id: string | number | null, result: unknown): JsonRpcSuccess {
  return {
    jsonrpc: "2.0",
    id,
    result
  };
}

function failure(id: string | number | null, code: number, message: string, data?: unknown): JsonRpcFailure {
  return {
    jsonrpc: "2.0",
    id,
    error: {
      code,
      message,
      data
    }
  };
}
