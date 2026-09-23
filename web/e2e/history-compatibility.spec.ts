import { expect, test } from "@playwright/test";

test("history remains usable when a result has no evidence or replay capability", async ({
  page,
}) => {
  await page.goto("/en");
  await page.getByLabel("Research question").fill("Legacy compatibility demo");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByText("Research synthesis")).toBeVisible({
    timeout: 15_000,
  });
  await page.goto("/en/history");
  await expect(
    page.getByRole("heading", { name: "Research history" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Legacy compatibility demo" }).first(),
  ).toBeVisible();
});
