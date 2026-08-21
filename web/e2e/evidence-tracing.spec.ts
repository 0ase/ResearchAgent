import { expect, test } from "@playwright/test";

test("traces a report citation to evidence and paper details", async ({
  page,
}) => {
  await page.goto("/en");
  await page.getByLabel("Research question").fill("Evidence tracing demo");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByText("Research synthesis")).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("button", { name: /open citation 1/i }).click();
  await expect(
    page.getByRole("region", { name: "Evidence details" }),
  ).toContainText("Hybrid retrieval improves grounding");
  await page.getByRole("button", { name: /open paper/i }).click();
  await expect(
    page.getByRole("complementary", { name: "Paper details" }),
  ).toContainText("Hybrid retrieval");
});
