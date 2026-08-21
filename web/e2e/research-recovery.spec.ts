import { expect, test } from "@playwright/test";

test("recovers a running task after refresh and re-entry from history", async ({
  page,
}) => {
  await page.goto("/en");
  await page.getByLabel("Research question").fill("History recovery demo");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page).toHaveURL(/\/research\//);
  await expect(
    page.getByRole("navigation", { name: "Stage detail" }),
  ).toBeVisible();

  await page.reload();
  await expect(page.getByText("Research synthesis")).toBeVisible({
    timeout: 15_000,
  });
  await page.goto("/en/history");
  await expect(
    page.getByRole("link", { name: "History recovery demo" }).first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "History recovery demo" })
    .first()
    .click();
  await expect(page.getByText("Research synthesis")).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("tab", { name: /Papers \(5\)/ }).click();
  await expect(page.getByRole("button", { name: /^Paper:/ })).toHaveCount(5);
});

test("cancels an active task and preserves the terminal recovery path", async ({
  page,
}) => {
  await page.goto("/en");
  await page
    .getByLabel("Research question")
    .fill("Cancel this deterministic task");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page).toHaveURL(/\/research\//);
  await page.getByRole("button", { name: "Cancel task" }).first().click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancel task" })
    .click();
  await expect(page.getByText("Research cancelled")).toBeVisible({
    timeout: 10_000,
  });
  await expect(
    page.getByRole("link", { name: "History" }).last(),
  ).toBeVisible();
});
