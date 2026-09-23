import type { paths } from "@/lib/api/schema";
import type { ResearchEvent } from "@/lib/events/types";
import { researchEventSchema } from "@/lib/events/schemas";
import {
  createTaskResponseSchema,
  deepSeekSettingsSchema,
  emptyResponseSchema,
  researchResultSchema,
  taskHistorySchema,
  taskSnapshotSchema,
} from "@/lib/api/response-schemas";

import {
  ApiHttpError,
  ApiNetworkError,
  ApiResponseValidationError,
  parseErrorEnvelope,
} from "@/lib/api/errors";

export {
  ApiHttpError,
  ApiNetworkError,
  ApiResponseValidationError,
} from "@/lib/api/errors";

export type ResponseParser<T> = (value: unknown) => T;

export type CreateTaskRequest =
  paths["/api/v1/research/tasks"]["post"]["requestBody"] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

export type CreateTaskResponse =
  paths["/api/v1/research/tasks"]["post"]["responses"][202] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

export type ActiveTaskResponse =
  paths["/api/v1/research/tasks/active"]["get"]["responses"][200] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

export type TaskSnapshotResponse =
  paths["/api/v1/research/tasks/{task_id}"]["get"]["responses"][200] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

export type ResearchTaskResultResponse =
  paths["/api/v1/research/tasks/{task_id}/result"]["get"]["responses"][200] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

export type DeepSeekSettingsResponse =
  paths["/api/v1/settings/deepseek"]["get"]["responses"][200] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

export type UpdateDeepSeekSettingsRequest =
  paths["/api/v1/settings/deepseek"]["put"]["requestBody"] extends {
    content: { "application/json": infer Body };
  }
    ? Body
    : never;

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, "") ||
    DEFAULT_API_BASE_URL
  );
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  parser?: ResponseParser<T>,
): Promise<T | undefined> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    throw new ApiNetworkError(error);
  }

  if (response.status === 204) {
    return undefined;
  }

  const body = await readJson(response);
  if (!response.ok) {
    const envelope = parseErrorEnvelope(body);
    if (envelope) {
      throw new ApiHttpError(response.status, envelope);
    }
    throw new ApiHttpError(response.status, {
      error: {
        code: "HTTP_ERROR",
        message: `请求失败（${response.status}）`,
        retryable: response.status >= 500,
        request_id: "unknown",
      },
    });
  }

  if (!parser) {
    return body as T;
  }

  try {
    return parser(body);
  } catch (error) {
    throw new ApiResponseValidationError(error);
  }
}

export function createResearchTask(
  request: CreateTaskRequest,
): Promise<CreateTaskResponse | undefined> {
  return apiRequest<CreateTaskResponse>(
    "/api/v1/research/tasks",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
    (value) => createTaskResponseSchema.parse(value) as CreateTaskResponse,
  );
}

export function getActiveTask(): Promise<ActiveTaskResponse | undefined> {
  return apiRequest<ActiveTaskResponse>(
    "/api/v1/research/tasks/active",
    undefined,
    (value) => taskSnapshotSchema.parse(value) as ActiveTaskResponse,
  );
}

export function getResearchTask(
  taskId: string,
): Promise<TaskSnapshotResponse | undefined> {
  return apiRequest<TaskSnapshotResponse>(
    `/api/v1/research/tasks/${encodeURIComponent(taskId)}`,
    undefined,
    (value) => taskSnapshotSchema.parse(value) as TaskSnapshotResponse,
  );
}

export function cancelResearchTask(
  taskId: string,
): Promise<TaskSnapshotResponse | undefined> {
  return apiRequest<TaskSnapshotResponse>(
    `/api/v1/research/tasks/${encodeURIComponent(taskId)}/cancel`,
    { method: "POST" },
    (value) => taskSnapshotSchema.parse(value) as TaskSnapshotResponse,
  );
}

export function retryResearchTask(
  taskId: string,
): Promise<TaskSnapshotResponse | undefined> {
  return apiRequest<TaskSnapshotResponse>(
    `/api/v1/research/tasks/${encodeURIComponent(taskId)}/retry`,
    { method: "POST" },
    (value) => taskSnapshotSchema.parse(value) as TaskSnapshotResponse,
  );
}

export function getResearchResult(
  taskId: string,
): Promise<ResearchTaskResultResponse | undefined> {
  return apiRequest<ResearchTaskResultResponse>(
    `/api/v1/research/tasks/${encodeURIComponent(taskId)}/result`,
    undefined,
    (value) => researchResultSchema.parse(value) as ResearchTaskResultResponse,
  );
}

export async function getResearchEvents(
  taskId: string,
): Promise<ResearchEvent[]> {
  let response: Response;
  try {
    response = await fetch(
      `${getApiBaseUrl()}/api/v1/research/tasks/${encodeURIComponent(taskId)}/events?after=0`,
      { headers: { Accept: "text/event-stream" } },
    );
  } catch (error) {
    throw new ApiNetworkError(error);
  }
  if (!response.ok)
    throw new ApiHttpError(response.status, {
      error: {
        code: "EVENTS_HTTP_ERROR",
        message: `事件读取失败（${response.status}）`,
        retryable: response.status >= 500,
        request_id: "unknown",
      },
    });
  const text = await response.text();
  return text
    .split(/\r?\n\r?\n/)
    .map((block) =>
      block
        .split(/\r?\n/)
        .find((line) => line.startsWith("data: "))
        ?.slice(6),
    )
    .filter((data): data is string => Boolean(data))
    .flatMap((data) => {
      try {
        const parsed = researchEventSchema.safeParse(JSON.parse(data));
        return parsed.success ? [parsed.data as ResearchEvent] : [];
      } catch {
        return [];
      }
    });
}

export function getResearchHistory(limit = 20) {
  return apiRequest<TaskSnapshotResponse[]>(
    `/api/v1/research/history?limit=${limit}`,
    undefined,
    (value) => taskHistorySchema.parse(value) as TaskSnapshotResponse[],
  );
}

export function updateResearchTask(
  taskId: string,
  title: string,
): Promise<TaskSnapshotResponse | undefined> {
  return apiRequest<TaskSnapshotResponse>(
    `/api/v1/research/tasks/${encodeURIComponent(taskId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ title }),
    },
    (value) => taskSnapshotSchema.parse(value) as TaskSnapshotResponse,
  );
}

export function deleteResearchTask(taskId: string): Promise<undefined> {
  return apiRequest<undefined>(
    `/api/v1/research/tasks/${encodeURIComponent(taskId)}`,
    { method: "DELETE" },
    (value) => emptyResponseSchema.parse(value),
  ).then(() => undefined);
}

export function getDeepSeekSettings(): Promise<
  DeepSeekSettingsResponse | undefined
> {
  return apiRequest<DeepSeekSettingsResponse>(
    "/api/v1/settings/deepseek",
    undefined,
    (value) => deepSeekSettingsSchema.parse(value) as DeepSeekSettingsResponse,
  );
}

export function updateDeepSeekSettings(
  request: UpdateDeepSeekSettingsRequest,
): Promise<DeepSeekSettingsResponse | undefined> {
  return apiRequest<DeepSeekSettingsResponse>(
    "/api/v1/settings/deepseek",
    {
      method: "PUT",
      body: JSON.stringify(request),
    },
    (value) => deepSeekSettingsSchema.parse(value) as DeepSeekSettingsResponse,
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    throw new ApiResponseValidationError(error);
  }
}
