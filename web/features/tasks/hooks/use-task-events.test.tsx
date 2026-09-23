import { act, render, renderHook, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";
import { TaskEventsProvider, useTaskEvents } from "@/features/tasks/hooks/use-task-events";

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
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
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
  return <Providers><TaskEventsProvider taskId="task-live">{children}</TaskEventsProvider></Providers>;
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
      expect(result.current.connectionStatus).toBe("connecting"),
    );

    expect(MockEventSource.instances[0].url).toContain(
      "/api/v1/research/tasks/task-live/events?after=7",
    );
    act(() => MockEventSource.instances[0].onopen?.());
    expect(result.current.connectionStatus).toBe("connected");
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
      expect(result.current.connectionStatus).toBe("connecting"),
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
      expect(result.current.connectionStatus).toBe("connecting"),
    );
    expect(result.current.task?.status).toBe("running");
    const source = MockEventSource.instances[0];
    act(() => source.onopen?.());
    expect(result.current.connectionStatus).toBe("connected");
    act(() => source.onerror?.());
    expect(result.current.connectionStatus).toBe("reconnecting");
    act(() => source.onopen?.());
    expect(result.current.connectionStatus).toBe("connected");
    expect(MockEventSource.instances).toHaveLength(1);
  });

  it("does not reopen SSE for an already terminal snapshot", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ...snapshot, status: "completed" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useTaskEvents("task-live"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.connectionStatus).toBe("closed"));
    expect(result.current.replayState?.isTerminal).toBe(true);
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("shares a single connection across consumers and panel remounts in StrictMode", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(snapshot), {
      status: 200, headers: { "content-type": "application/json" },
    }));
    function Consumer() { useTaskEvents("task-live"); return null; }
    function View({ panel }: { panel: boolean }) {
      return <StrictMode><Providers><TaskEventsProvider taskId="task-live">
        <Consumer />{panel && <Consumer />}
      </TaskEventsProvider></Providers></StrictMode>;
    }
    const view = render(<View panel />);
    await waitFor(() => expect(MockEventSource.instances.filter(s => !s.closed)).toHaveLength(1));
    const count = MockEventSource.instances.length;
    view.rerender(<View panel={false} />);
    view.rerender(<View panel />);
    expect(MockEventSource.instances).toHaveLength(count);
    view.unmount();
    expect(MockEventSource.instances.filter(s => !s.closed)).toHaveLength(0);
  });

  it("closes the old task stream before switching scope and rejects stale events", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(JSON.stringify({
      ...snapshot, id: String(input).includes("task-next") ? "task-next" : "task-live",
    }), { status: 200, headers: { "content-type": "application/json" } }));
    function Consumer({ id }: { id: string }) {
      const state = useTaskEvents(id);
      return <output>{state.replayState?.taskId}:{state.replayState?.lastSequence}</output>;
    }
    function View({ id }: { id: string }) {
      return <Providers><TaskEventsProvider taskId={id}><Consumer id={id} /></TaskEventsProvider></Providers>;
    }
    const view = render(<View id="task-live" />);
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const old = MockEventSource.instances[0];
    view.rerender(<View id="task-next" />);
    expect(old.closed).toBe(true);
    await waitFor(() => expect(view.getByRole("status")).toHaveTextContent("task-next:7"));
    expect(MockEventSource.instances.filter(s => !s.closed)).toHaveLength(1);
    act(() => old.emit("task.completed", {
      schema_version: 1, task_id: "task-live", sequence: 99, event_type: "task.completed",
      stage: null, level: "info", payload: {}, occurred_at: "2026-08-19T10:00:08Z",
    }));
    expect(view.getByRole("status")).toHaveTextContent("task-next:7");
  });
});
