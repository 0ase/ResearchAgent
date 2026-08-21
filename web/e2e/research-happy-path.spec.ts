import { expect, test } from "@playwright/test";

test("creates a deterministic research task and reaches the report", async ({
  page,
}) => {
  await page.goto("/en");
  await page
    .getByLabel("Research question")
    .fill("How do retrieval systems improve scientific discovery?");
  await page.getByRole("button", { name: "Start research" }).click();

  await expect(page).toHaveURL(/\/research\//);
  await expect(page.getByText("Research synthesis")).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("tab", { name: "Report" })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Papers \(5\)/ })).toBeVisible();

  await page.getByRole("tab", { name: /Papers \(5\)/ }).click();
  await expect(
    page.getByRole("button", { name: /Paper: Hybrid retrieval/i }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Paper: Hybrid retrieval/i }).click();
  await expect(
    page
      .getByRole("complementary", { name: "Context panel" })
      .getByRole("complementary", { name: "Paper details" }),
  ).toContainText("Hybrid retrieval");
});
