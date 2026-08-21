import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import {
  ApiHttpError,
  ApiResponseValidationError,
  apiRequest,
  type CreateTaskRequest,
  createResearchTask,
  getActiveTask,
} from "@/lib/api/client";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

describe("research API client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("constructs requests from NEXT_PUBLIC_API_BASE_URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ ok: true }));

    await apiRequest("/api/v1/research/history");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://api.example.test/api/v1/research/history");
    expect(new Headers(init?.headers).get("Accept")).toBe("application/json");
  });

  it("returns undefined for 204 without parsing JSON", async () => {
    const response = new Response(null, { status: 204 });
    vi.spyOn(response, "json").mockRejectedValue(new Error("must not parse"));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    await expect(getActiveTask()).resolves.toBeUndefined();
  });

  it("turns an error envelope into an ApiHttpError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "ACTIVE_TASK_EXISTS",
            message: "已有研究任务正在运行",
            retryable: false,
            request_id: "req-123",
            details: { task_id: "task-1" },
          },
        },
        409,
      ),
    );

    const error = await apiRequest("/api/v1/research/tasks", {
      method: "POST",
    }).catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiHttpError);
    expect(error).toMatchObject({
      status: 409,
      code: "ACTIVE_TASK_EXISTS",
      requestId: "req-123",
    });
  });

  it("reports a recognizable error when the response fails validation", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ ok: 1 }));

    const error = await apiRequest(
      "/api/v1/research/history",
      undefined,
      (value) => z.object({ id: z.string() }).parse(value),
    ).catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiResponseValidationError);
    expect(error).toMatchObject({ code: "INVALID_RESPONSE" });
  });

  it("keeps the caller-provided Client Request ID stable", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(
        jsonResponse(
          {
            task: {
              id: "task-1",
              client_request_id: "client-request-stable",
              query: "retrieval augmented generation",
              title: "Retrieval augmented generation",
              status: "queued",
              effective_locale: "en",
              last_sequence: 0,
              created_at: "2026-08-19T10:00:00Z",
            },
            links: {
              self: "/api/v1/research/tasks/task-1",
              events: "/api/v1/research/tasks/task-1/events",
              result: "/api/v1/research/tasks/task-1/result",
            },
          },
          202,
        ),
      ),
    );
    const request: CreateTaskRequest = {
      client_request_id: "client-request-stable",
      query: "retrieval augmented generation",
      options: {
        max_papers: 10,
        sources: ["arxiv"],
        output_language: "auto",
      },
    };

    await createResearchTask(request);
    await createResearchTask(request);

    const bodies = fetchMock.mock.calls.map(([, init]) =>
      JSON.parse(String(init?.body)),
    );
    expect(bodies).toHaveLength(2);
    expect(bodies.map((body) => body.client_request_id)).toEqual([
      "client-request-stable",
      "client-request-stable",
    ]);
  });
});
