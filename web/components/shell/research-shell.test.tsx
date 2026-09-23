import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { QueryClient, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";
import NotFound from "@/app/not-found";
import { ContextPanel } from "@/components/shell/context-panel";
import { ResearchShell } from "@/components/shell/research-shell";
import { TaskSidebar } from "@/components/shell/task-sidebar";
import { resetUiStore } from "@/stores/ui-store";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

function QueryClientProbe({
  onClient,
}: {
  onClient: (client: QueryClient) => void;
}) {
  const client = useQueryClient();
  const reported = useRef(false);
  useEffect(() => {
    if (!reported.current) {
      reported.current = true;
      onClient(client);
    }
  }, [client, onClient]);
  return <span>query client ready</span>;
}

describe("research workspace shell", () => {
  afterEach(() => {
    resetUiStore();
    document.documentElement.removeAttribute("data-theme");
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("creates one QueryClient for the browser session", () => {
    const clients: QueryClient[] = [];
    const { rerender } = render(
      <Providers locale="en">
        <QueryClientProbe onClient={(client) => clients.push(client)} />
      </Providers>,
    );

    rerender(
      <Providers locale="en">
        <QueryClientProbe onClient={(client) => clients.push(client)} />
      </Providers>,
    );

    expect(clients).toHaveLength(1);
  });

  it("places the theme toggle before the language switcher", () => {
    render(
      <Providers locale="en">
        <ResearchShell>
          <h1>Theme controls</h1>
        </ResearchShell>
      </Providers>,
    );

    const toggle = screen.getByRole("button", {
      name: "Switch to dark theme",
    });
    const language = screen.getByRole("button", { name: "中文" });
    expect(
      toggle.compareDocumentPosition(language) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });


  it("renders task navigation, central content, and context panel", () => {
    render(
      <Providers locale="en">
        <ResearchShell taskId="task-123">
          <h1>Research report</h1>
        </ResearchShell>
      </Providers>,
    );

    expect(
      screen.getByRole("complementary", { name: "Task navigation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveTextContent("Research report");
    expect(
      screen.getByRole("complementary", { name: "Context panel" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Research task" }),
    ).toBeInTheDocument();
    expect(
      within(
        screen.getByRole("complementary", { name: "Task navigation" }),
      ).queryByText("task-123"),
    ).not.toBeInTheDocument();
  });

  it("shows the current task title instead of its ID", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/research/tasks/task-123")) {
        return Promise.resolve(
          jsonResponse({
            id: "task-123",
            client_request_id: "client-task-123",
            query: "How reliable is graph retrieval?",
            title: "Graph retrieval reliability",
            status: "running",
            effective_locale: "en",
            last_sequence: 0,
            created_at: "2026-08-23T12:00:00Z",
          }),
        );
      }
      return Promise.resolve(jsonResponse([]));
    });

    render(
      <Providers locale="en">
        <TaskSidebar taskId="task-123" />
      </Providers>,
    );

    expect(
      await screen.findByRole("link", {
        name: "Graph retrieval reliability",
      }),
    ).toHaveAttribute("href", "/research/task-123");
    expect(screen.queryByText("task-123")).not.toBeInTheDocument();
  });

  it("fully hides and restores the task sidebar without unmounting content", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <ResearchShell>
          <h1>Persistent workspace</h1>
        </ResearchShell>
      </Providers>,
    );

    await user.click(
      screen.getByRole("button", { name: "Collapse task sidebar" }),
    );

    expect(
      screen.queryByRole("complementary", { name: "Task navigation" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveTextContent("Persistent workspace");

    await user.click(
      screen.getByRole("button", { name: "Expand task sidebar" }),
    );
    expect(
      screen.getByRole("complementary", { name: "Task navigation" }),
    ).toBeInTheDocument();
  });

  it("collapses the right panel without unmounting central content", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <ResearchShell>
          <h1>Persistent report</h1>
        </ResearchShell>
      </Providers>,
    );

    await user.click(
      screen.getByRole("button", { name: "Collapse context panel" }),
    );

    expect(screen.getByRole("main")).toHaveTextContent("Persistent report");
    expect(
      screen.getAllByRole("button", { name: "Expand context panel" }),
    ).not.toHaveLength(0);
  });

  it("switches the context panel tab without affecting the central area", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <ResearchShell>
          <h1>Stable report</h1>
        </ResearchShell>
      </Providers>,
    );

    await user.click(screen.getByRole("tab", { name: "Papers" }));

    expect(screen.getByRole("tab", { name: "Papers" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("main")).toHaveTextContent("Stable report");
  });

  it("provides home and history entry points from not-found", () => {
    render(
      <Providers locale="en">
        <NotFound />
      </Providers>,
    );

    expect(screen.getByRole("link", { name: /home/i })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: /history/i })).toHaveAttribute(
      "href",
      "/history",
    );
    expect(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    ).toBeInTheDocument();
  });

  it("keeps ContextPanel independently renderable for route composition", () => {
    render(
      <Providers locale="en">
        <ContextPanel />
      </Providers>,
    );

    expect(screen.getByRole("tab", { name: "Evidence" })).toBeInTheDocument();
  });
});
