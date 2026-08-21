import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { QueryClient, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { Providers } from "@/app/providers";
import NotFound from "@/app/not-found";
import { ContextPanel } from "@/components/shell/context-panel";
import { ResearchShell } from "@/components/shell/research-shell";
import { resetUiStore } from "@/stores/ui-store";

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
    expect(screen.getByRole("link", { name: "task-123" })).toBeInTheDocument();
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
