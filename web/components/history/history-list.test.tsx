import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { HistoryList } from "@/components/history/history-list";
import type { TaskSnapshotResponse } from "@/lib/api/client";
import { Providers } from "@/app/providers";

const tasks = [
  {
    id: "task-new",
    client_request_id: "client-new",
    query: "Graph retrieval methods",
    title: "Graph retrieval",
    status: "completed",
    created_at: "2026-08-19T10:00:00Z",
    completed_at: "2026-08-19T10:03:00Z",
    statistics: { papers_count: 8, critique_score: 0.92, duration_ms: 180000 },
    available_actions: ["retry", "rename", "delete"],
  },
  {
    id: "task-old",
    client_request_id: "client-old",
    query: "Attention mechanisms",
    title: "Attention survey",
    status: "failed",
    created_at: "2026-08-18T10:00:00Z",
    completed_at: null,
    statistics: { papers_count: 3, critique_score: 0.45, duration_ms: 90000 },
    available_actions: ["retry", "rename", "delete"],
  },
  {
    id: "task-active",
    client_request_id: "client-active",
    query: "Active task",
    title: "Active research",
    status: "running",
    created_at: "2026-08-17T10:00:00Z",
    completed_at: null,
    statistics: { papers_count: 1 },
    available_actions: ["cancel"],
  },
] as unknown as TaskSnapshotResponse[];

describe("HistoryList", () => {
  it("sorts newest first and filters by search and status", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <HistoryList tasks={tasks} />
      </Providers>,
    );

    const rows = screen.getAllByRole("article");
    expect(rows[0]).toHaveTextContent("Graph retrieval");
    expect(rows[1]).toHaveTextContent("Attention survey");

    await user.type(screen.getByLabelText("Search history"), "attention");
    expect(screen.getByText("Attention survey")).toBeInTheDocument();
    expect(screen.queryByText("Graph retrieval")).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("Search history"));
    await user.selectOptions(screen.getByLabelText("Status"), "failed");
    expect(screen.getByText("Attention survey")).toBeInTheDocument();
    expect(screen.queryByText("Graph retrieval")).not.toBeInTheDocument();
  });

  it("renames a task, confirms deletion, and keeps active deletion disabled", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn(async () => undefined);
    const onDelete = vi.fn(async () => undefined);
    render(
      <Providers locale="en">
        <HistoryList
          tasks={tasks}
          onRename={onRename}
          onDelete={onDelete}
          activeTaskId="task-active"
        />
      </Providers>,
    );

    await user.click(
      screen.getByRole("button", { name: "Rename Graph retrieval" }),
    );
    await user.clear(screen.getByLabelText("New title"));
    await user.type(screen.getByLabelText("New title"), "Updated graph study");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(onRename).toHaveBeenCalledWith("task-new", "Updated graph study");

    await user.click(
      screen.getByRole("button", { name: "Delete Graph retrieval" }),
    );
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledWith("task-new");
    expect(
      screen.getByRole("button", { name: "Delete Active research" }),
    ).toBeDisabled();
  });
});
