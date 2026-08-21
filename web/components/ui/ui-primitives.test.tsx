import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

describe("UI primitives", () => {
  it.each(["primary", "secondary", "ghost", "destructive"] as const)(
    "maps the %s button variant",
    (variant) => {
      render(<Button variant={variant}>Action</Button>);

      expect(screen.getByRole("button", { name: "Action" })).toHaveAttribute(
        "data-variant",
        variant,
      );
    },
  );

  it("moves focus into Dialog content, closes on Escape, and restores trigger focus", async () => {
    const user = userEvent.setup();
    render(
      <Dialog>
        <DialogTrigger asChild>
          <Button>Open settings</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle>Settings</DialogTitle>
          <button type="button">Inside</button>
        </DialogContent>
      </Dialog>,
    );

    const trigger = screen.getByRole("button", { name: "Open settings" });
    await user.click(trigger);
    expect(screen.getByRole("button", { name: "Inside" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("supports keyboard navigation between Tabs", async () => {
    const user = userEvent.setup();
    render(
      <Tabs defaultValue="evidence">
        <TabsList aria-label="Context">
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
          <TabsTrigger value="papers">Papers</TabsTrigger>
        </TabsList>
        <TabsContent value="evidence">Evidence content</TabsContent>
        <TabsContent value="papers">Papers content</TabsContent>
      </Tabs>,
    );

    const evidence = screen.getByRole("tab", { name: "Evidence" });
    await user.click(evidence);
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Papers" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText("Papers content")).toBeVisible();
  });

  it("keeps a Tooltip supplemental to the trigger accessible name", async () => {
    const user = userEvent.setup();
    render(
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" aria-label="Cancel research task">
              Cancel
            </button>
          </TooltipTrigger>
          <TooltipContent>Stop the active task</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );

    const trigger = screen.getByRole("button", {
      name: "Cancel research task",
    });
    await user.hover(trigger);

    expect(trigger).toHaveAccessibleName("Cancel research task");
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Stop the active task",
    );
  });

  it("renders an Inline Alert with icon, message, and alert semantics", () => {
    render(
      <InlineAlert tone="warning">
        Search is taking longer than usual.
      </InlineAlert>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Search is taking longer than usual.",
    );
    expect(screen.getByRole("alert").querySelector("svg")).toBeInTheDocument();
  });
});
