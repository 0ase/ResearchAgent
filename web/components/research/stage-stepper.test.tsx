import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StageStepper } from "@/components/research/stage-stepper";
import { createInitialReplayState } from "@/lib/events/reducer";
import { Providers } from "@/app/providers";

function stateWithStages() {
  const state = createInitialReplayState("task-stepper");
  state.stages.orchestrate.status = "completed";
  state.stages.search.status = "running";
  state.stages.filter.status = "warning";
  state.stages.read.status = "failed";
  state.stages.critic.attempt = 2;
  return state;
}

describe("StageStepper", () => {
  it("renders waiting, running, completed, warning, failed, and cancelled statuses", () => {
    const state = stateWithStages();
    state.stages.synthesize.status = "cancelled";
    render(
      <Providers locale="en">
        <StageStepper state={state} />
      </Providers>,
    );

    expect(
      screen.getByRole("button", { name: /plan.*completed/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /search.*running/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /select.*warning/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /read.*failed/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /synthesize.*cancelled/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /analyze.*pending/i }),
    ).toBeInTheDocument();
  });

  it("shows the critic revision attempt and opens the selected stage", async () => {
    const user = userEvent.setup();
    const onSelectStage = vi.fn();
    render(
      <Providers locale="en">
        <StageStepper state={stateWithStages()} onSelectStage={onSelectStage} />
      </Providers>,
    );

    expect(screen.getByText("Attempt 2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /search.*running/i }));
    expect(onSelectStage).toHaveBeenCalledWith("search");
  });
});
