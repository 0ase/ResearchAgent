import { expect, test } from "@playwright/test";

test("uses Chinese by default and persists an explicit English choice", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("heading", { name: "开始一个研究任务" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "English" }).click();
  await expect(page).toHaveURL(/\/en$/);
  await expect(
    page.getByRole("heading", { name: "Start a research task" }),
  ).toBeVisible();

  await expect
    .poll(async () => {
      const cookie = (await context.cookies()).find(
        (item) => item.name === "RESEARCH_AGENT_LOCALE",
      );
      return cookie?.value;
    })
    .toBe("en");

  await page.getByRole("button", { name: "中文" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("heading", { name: "开始一个研究任务" }),
  ).toBeVisible();
});
