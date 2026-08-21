import { userEvent } from "@testing-library/user-event";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ResearchComposer } from "@/components/research/research-composer";
import { Providers } from "@/app/providers";

function renderComposer(
  createTask = vi.fn(async () => ({
    task: { id: "task-created" },
    links: {},
  })),
) {
  const onCreated = vi.fn();
  render(
    <Providers locale="en">
      <ResearchComposer createTask={createTask} onCreated={onCreated} />
    </Providers>,
  );
  return { createTask, onCreated };
}

describe("ResearchComposer", () => {
  it("starts with the documented defaults", async () => {
    renderComposer();

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /research overrides/i }),
    );
    expect(
      screen.getByRole("spinbutton", { name: /maximum papers/i }),
    ).toHaveValue(20);
    expect(
      screen.queryByRole("combobox", { name: /output language/i }),
    ).not.toBeInTheDocument();
    for (const source of ["arXiv", "Semantic Scholar", "PubMed", "Crossref"]) {
      expect(screen.getByRole("checkbox", { name: source })).toBeChecked();
    }
  });

  it("rejects empty queries and queries over 2,000 characters", async () => {
    const user = userEvent.setup();
    const { createTask } = renderComposer();
    const query = screen.getByRole("textbox", { name: /research question/i });

    await user.click(screen.getByRole("button", { name: /start research/i }));
    expect(createTask).not.toHaveBeenCalled();
    expect(screen.getByText(/enter a research question/i)).toBeInTheDocument();

    await user.clear(query);
    fireEvent.change(query, { target: { value: "a".repeat(2001) } });
    await user.click(screen.getByRole("button", { name: /start research/i }));

    expect(screen.getByText(/2,000 characters/i)).toBeInTheDocument();
    expect(createTask).not.toHaveBeenCalled();
  });

  it("requires at least one source", async () => {
    const user = userEvent.setup();
    const { createTask } = renderComposer();

    await user.click(
      screen.getByRole("button", { name: /research overrides/i }),
    );
    for (const source of ["arXiv", "Semantic Scholar", "PubMed", "Crossref"]) {
      await user.click(screen.getByRole("checkbox", { name: source }));
    }
    await user.type(
      screen.getByRole("textbox", { name: /research question/i }),
      "Compare retrieval methods",
    );
    await user.click(screen.getByRole("button", { name: /start research/i }));

    expect(screen.getByText(/select at least one source/i)).toBeInTheDocument();
    expect(createTask).not.toHaveBeenCalled();
  });

  it("fills an example without submitting", async () => {
    const user = userEvent.setup();
    const { createTask } = renderComposer();
    const exampleLabel = "Latest advances in Transformer attention";
    const exampleQuery =
      "What advances have been made in Transformer attention since 2023?";

    await user.click(screen.getByRole("button", { name: exampleLabel }));

    expect(
      screen.getByRole("textbox", { name: /research question/i }),
    ).toHaveValue(exampleQuery);
    expect(createTask).not.toHaveBeenCalled();
  });

  it("uses Ctrl/Cmd+Enter to submit while ordinary Enter remains a newline", async () => {
    const user = userEvent.setup();
    const { createTask } = renderComposer();
    const query = screen.getByRole("textbox", { name: /research question/i });

    await user.type(query, "First line");
    await user.keyboard("{Enter}");
    expect(query).toHaveValue("First line\n");
    await user.type(query, "Second line");
    await user.keyboard("{Control>}{Enter}{/Control}");

    await waitFor(() => expect(createTask).toHaveBeenCalledTimes(1));
  });

  it("disables duplicate submissions and routes after a 202 response", async () => {
    const user = userEvent.setup();
    let resolve:
      | ((value: {
          task: { id: string };
          links: Record<string, string>;
        }) => void)
      | undefined;
    const createTask = vi.fn(
      () =>
        new Promise<{ task: { id: string }; links: Record<string, string> }>(
          (done) => {
            resolve = done;
          },
        ),
    );
    const { onCreated } = renderComposer(createTask);
    await user.type(
      screen.getByRole("textbox", { name: /research question/i }),
      "A research question",
    );
    const button = screen.getByRole("button", { name: /start research/i });

    await user.click(button);
    await user.click(button);
    expect(createTask).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();

    resolve?.({ task: { id: "task-202" }, links: {} });
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith("task-202"));
  });

  it("shows an active-task entry point after a 409 response", async () => {
    const user = userEvent.setup();
    const createTask = vi.fn(async () => {
      const error = new Error("active") as Error & {
        status: number;
        details: { task_id: string };
      };
      error.status = 409;
      error.details = { task_id: "active-task" };
      throw error;
    });
    renderComposer(createTask);

    await user.type(
      screen.getByRole("textbox", { name: /research question/i }),
      "Research question",
    );
    await user.click(screen.getByRole("button", { name: /start research/i }));

    expect(
      await screen.findByRole("link", { name: /return to active task/i }),
    ).toHaveAttribute("href", "/research/active-task");
  });
});
