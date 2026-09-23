import { expect, test } from "@playwright/test";

test("replays persisted agent events with controls and critic revisions", async ({
  page,
}) => {
  await page.goto("/en");
  await page.getByLabel("Research question").fill("Replay demo");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByText("Research synthesis")).toBeVisible({
    timeout: 15_000,
  });
  await page
    .getByLabel("Research views")
    .getByRole("tab", { name: "Run details" })
    .click();
  await page.getByText("Open execution replay").click();
  await expect(
    page.getByRole("heading", { name: "Agent replay" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "2x speed" }).click();
  await expect(page.getByRole("button", { name: "2x speed" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByRole("button", { name: "Next replay event" }).click();
  await expect(
    page.getByRole("region", { name: "Event timeline" }),
  ).toBeVisible();
});
