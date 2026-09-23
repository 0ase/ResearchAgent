import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
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

  it("keeps primary interaction states tied to theme tokens", () => {
    render(<Button variant="primary">Primary action</Button>);

    expect(screen.getByRole("button", { name: "Primary action" })).toHaveClass(
      "hover:bg-[var(--color-primary-hover)]",
      "active:bg-[var(--color-primary-active)]",
      "focus-visible:ring-[var(--color-focus)]",
    );
  });

  it.each([
    [
      "neutral",
      "border-[var(--color-border)]",
      "bg-[var(--color-surface-subtle)]",
      "text-[var(--color-text-muted)]",
    ],
    [
      "accent",
      "border-[var(--color-primary-border)]",
      "bg-[var(--color-primary-subtle)]",
      "text-[var(--color-primary)]",
    ],
    [
      "info",
      "border-[var(--color-info-border)]",
      "bg-[var(--color-info-subtle)]",
      "text-[var(--color-info)]",
    ],
    [
      "blue",
      "border-[var(--color-info-border)]",
      "bg-[var(--color-info-subtle)]",
      "text-[var(--color-info)]",
    ],
    [
      "success",
      "border-[var(--color-success-border)]",
      "bg-[var(--color-success-subtle)]",
      "text-[var(--color-success)]",
    ],
    [
      "warning",
      "border-[var(--color-warning-border)]",
      "bg-[var(--color-warning-subtle)]",
      "text-[var(--color-warning)]",
    ],
    [
      "error",
      "border-[var(--color-error-border)]",
      "bg-[var(--color-error-subtle)]",
      "text-[var(--color-error)]",
    ],
  ] as const)(
    "maps the %s badge to semantic tokens",
    (variant, border, background, text) => {
      render(<Badge variant={variant}>Status</Badge>);

      expect(screen.getByText("Status")).toHaveClass(border, background, text);
    },
  );

  it("uses the readable muted token for input placeholders", () => {
    render(
      <>
        <Input placeholder="Input placeholder" />
        <Textarea placeholder="Textarea placeholder" />
      </>,
    );

    expect(screen.getByPlaceholderText("Input placeholder")).toHaveClass(
      "placeholder:text-[var(--color-text-muted)]",
    );
    expect(screen.getByPlaceholderText("Textarea placeholder")).toHaveClass(
      "placeholder:text-[var(--color-text-muted)]",
    );
  });

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
