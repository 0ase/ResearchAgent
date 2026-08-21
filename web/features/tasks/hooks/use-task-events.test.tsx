import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";
import { useTaskEvents } from "@/features/tasks/hooks/use-task-events";

const snapshot = {
  id: "task-live",
  client_request_id: "client-live",
  query: "How does retrieval work?",
  title: "Retrieval research",
  status: "running",
  effective_locale: "en",
  current_stage: "search",
  options: {},
  progress: { message: "Searching" },
  stages: [],
  statistics: {},
  last_sequence: 7,
  available_actions: ["cancel"],
  created_at: "2026-08-19T10:00:00Z",
  started_at: "2026-08-19T10:00:01Z",
  completed_at: null,
  parent_task_id: null,
  error_code: null,
  error_message: null,
};

class MockEventSource {
  static instances: MockEventSource[] = [];
  readonly url: string;
  closed = false;
  private listeners = new Map<string, (event: MessageEvent<string>) => void>();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    this.listeners.set(type, listener as (event: MessageEvent<string>) => void);
  }

  removeEventListener(type: string) {
    this.listeners.delete(type);
  }

  close() {
    this.closed = true;
  }

  emit(type: string, data: Record<string, unknown>) {
    this.listeners.get(type)?.(
      new MessageEvent(type, { data: JSON.stringify(data) }),
    );
  }
}

function wrapper({ children }: { children: React.ReactNode }) {
  return <Providers>{children}</Providers>;
}

describe("useTaskEvents", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/research/task-live");
  });

  afterEach(() => {
    MockEventSource.instances = [];
    vi.restoreAllMocks();
  });

  it("loads the snapshot before opening SSE from its last sequence", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(snapshot), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useTaskEvents("task-live"), {
      wrapper,
    });
    await waitFor(() =>
      expect(result.current.connectionStatus).toBe("connected"),
    );

    expect(MockEventSource.instances[0].url).toContain(
      "/api/v1/research/tasks/task-live/events?after=7",
    );
  });

  it("validates named events, ignores duplicates, and closes on terminal event", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(snapshot), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const { result, unmount } = renderHook(() => useTaskEvents("task-live"), {
      wrapper,
    });
    await waitFor(() =>
      expect(result.current.connectionStatus).toBe("connected"),
    );
    const source = MockEventSource.instances[0];
    const progress = {
      schema_version: 1,
      task_id: "task-live",
      sequence: 8,
      event_type: "stage.progress",
      stage: "search",
      level: "info",
      payload: { message: "Found 4 papers", metrics: { papers: 4 } },
      occurred_at: "2026-08-19T10:00:08Z",
    };

    source.emit("stage.progress", progress);
    source.emit("stage.progress", progress);
    await waitFor(() =>
      expect(result.current.replayState?.lastSequence).toBe(8),
    );
    expect(result.current.replayState?.metrics.papers).toBe(4);

    source.emit("task.completed", {
      ...progress,
      sequence: 9,
      event_type: "task.completed",
      stage: null,
      payload: {},
    });
    await waitFor(() =>
      expect(result.current.replayState?.taskStatus).toBe("completed"),
    );
    expect(source.closed).toBe(true);

    unmount();
    expect(source.closed).toBe(true);
  });

  it("reports reconnecting instead of failing when EventSource errors", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(snapshot), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useTaskEvents("task-live"), {
      wrapper,
    });
    await waitFor(() =>
      expect(result.current.connectionStatus).toBe("connected"),
    );
    expect(result.current.task?.status).toBe("running");
  });
});
