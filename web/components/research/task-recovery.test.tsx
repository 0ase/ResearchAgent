import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CancelTaskDialog } from "@/components/research/cancel-task-dialog";
import { TaskErrorState } from "@/components/research/task-error-state";
import { TaskOfflineState } from "@/components/research/task-offline-state";
import { TaskTerminalState } from "@/components/research/task-terminal-state";
import { Providers } from "@/app/providers";

describe("task recovery states", () => {
  it("requires explicit confirmation before cancelling", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <Providers locale="en">
        <CancelTaskDialog open onOpenChange={vi.fn()} onConfirm={onConfirm} />
      </Providers>,
    );

    expect(onConfirm).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Keep running" }));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("confirms cancellation only after pressing the destructive action", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn(async () => undefined);
    render(
      <Providers locale="en">
        <CancelTaskDialog open onOpenChange={vi.fn()} onConfirm={onConfirm} />
      </Providers>,
    );

    await user.click(screen.getByRole("button", { name: "Cancel task" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("distinguishes retryable failures, offline state, and preserved cancellation", async () => {
    const onRetry = vi.fn();
    render(
      <Providers locale="en">
        <>
          <TaskErrorState
            code="SEARCH_FAILED"
            message="Search failed"
            retryable
            onRetry={onRetry}
          />
          <TaskOfflineState />
          <TaskTerminalState status="cancelled" onRetry={onRetry} />
        </>
      </Providers>,
    );

    expect(screen.getByText(/error code: search_failed/i)).toBeInTheDocument();
    expect(screen.getByText(/you are offline/i)).toBeInTheDocument();
    expect(
      screen.getByText(/existing stages and artifacts/i),
    ).toBeInTheDocument();
    await userEvent
      .setup()
      .click(screen.getAllByRole("button", { name: /retry research/i })[0]);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
