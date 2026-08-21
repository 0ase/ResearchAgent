import { expect, test } from "@playwright/test";

test("Chinese research results expose multiple sources and accurate text states", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("研究问题")
    .fill("请比较多来源检索在科研问答中的优势和局限。");
  await page.getByRole("button", { name: "开始研究" }).click();

  await expect(page).toHaveURL(/\/research\//);
  await expect(page.getByText("研究综合报告")).toBeVisible({
    timeout: 15_000,
  });
  const papersTab = page.getByRole("tab", { name: /论文（5）/ });
  await expect(papersTab).toBeVisible();
  await papersTab.click();

  const paperRows = page.locator("article");
  await expect(paperRows.filter({ hasText: "arxiv" }).first()).toBeVisible();
  await expect(
    paperRows.filter({ hasText: "semantic_scholar" }).first(),
  ).toBeVisible();
  await expect(paperRows.filter({ hasText: "pubmed" }).first()).toBeVisible();

  const noAbstractPaper = page.getByRole("button", {
    name: /Full-text evaluation without an abstract/i,
  });
  await noAbstractPaper.click();
  const paperDetails = page
    .getByRole("complementary", { name: "上下文面板" })
    .getByRole("complementary", { name: "论文详情" });
  await expect(
    paperDetails,
  ).toContainText("暂无摘要");
  await expect(paperDetails).toContainText("全文可用，但该来源没有提供摘要。");

  const unavailablePaper = page.getByRole("button", {
    name: /Unavailable metadata record/i,
  });
  await expect(unavailablePaper).toContainText("暂无可读文本");
  await expect(unavailablePaper).not.toContainText("仅摘要");
});
