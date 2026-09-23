import { userEvent } from "@testing-library/user-event";
import { cleanup, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentReplay } from "@/components/replay/agent-replay";
import { Providers } from "@/app/providers";
import {
  criticRevisionEvents,
  failureEvents,
  successEvents,
} from "@/lib/events/fixtures";

describe("AgentReplay", () => {
  it("moves the cursor with previous/next and exposes public payloads", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <AgentReplay taskId="fixture-task" events={successEvents} />
      </Providers>,
    );

    expect(screen.getByText("Cursor 0 · queued")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next replay event" }));
    expect(screen.getByText(/Cursor 1/)).toBeInTheDocument();
    expect(screen.getAllByText("task.created").length).toBeGreaterThan(0);
  });

  it("shows critic revisions and terminal failure replay", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <AgentReplay taskId="fixture-task" events={criticRevisionEvents} />
      </Providers>,
    );
    for (let index = 0; index < criticRevisionEvents.length; index += 1) {
      await user.click(
        screen.getByRole("button", { name: "Next replay event" }),
      );
    }
    expect(screen.getByText(/Critic revision 2/)).toBeInTheDocument();

    cleanup();
    render(
      <Providers locale="en">
        <AgentReplay taskId="fixture-task" events={failureEvents} />
      </Providers>,
    );
    expect(
      screen.getByRole("region", { name: "Event timeline" }),
    ).toBeInTheDocument();
  });

  it("returns to the play state when the replay reaches its final event", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <AgentReplay taskId="fixture-task" events={successEvents} />
      </Providers>,
    );

    for (let index = 0; index < successEvents.length; index += 1) {
      await user.click(
        screen.getByRole("button", { name: "Next replay event" }),
      );
    }

    expect(
      screen.getByRole("button", { name: "Play replay" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Replay finished")).toBeInTheDocument();
  });
});
