import { expect, test } from "@playwright/test";

test("one task stream survives panel toggles and offline recovery", async ({ page, context }) => {
  await page.addInitScript(() => {
    const Native = window.EventSource;
    const metrics = { active: 0, peak: 0, created: 0 };
    Object.assign(window, { researchStreamMetrics: metrics });
    window.EventSource = class extends Native {
      private counted = true;
      constructor(url: string | URL, options?: EventSourceInit) {
        super(url, options);
        metrics.active += 1;
        metrics.created += 1;
        metrics.peak = Math.max(metrics.peak, metrics.active);
      }
      close() {
        if (this.counted) { metrics.active -= 1; this.counted = false; }
        super.close();
      }
    };
  });
  await page.goto("/en");
  await page.getByLabel("Research question").fill("SSE ownership reliability check");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page).toHaveURL(/\/research\//);
  const metrics = () => page.evaluate(() => (window as unknown as {
    researchStreamMetrics: { active: number; peak: number; created: number }
  }).researchStreamMetrics);
  await expect.poll(async () => (await metrics()).created).toBeGreaterThan(0);
  const created = (await metrics()).created;
  await page.getByRole("button", { name: "Collapse context panel" }).click();
  await page.getByRole("button", { name: "Expand context panel" }).first().click();
  expect((await metrics()).created).toBe(created);
  expect((await metrics()).peak).toBe(1);
  await context.setOffline(true);
  await page.waitForTimeout(300);
  await context.setOffline(false);
  await expect(page.getByText("Research synthesis")).toBeVisible({ timeout: 20_000 });
  await expect.poll(async () => (await metrics()).active).toBe(0);
  expect((await metrics()).peak).toBe(1);
});
