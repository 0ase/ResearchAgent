import { expect, test } from "@playwright/test";

test("opens settings from the companion and restores access when hidden", async ({
  page,
}) => {
  await page.goto("/en");
  const companion = page.getByRole("button", {
    name: /Research companion: idle; open settings/i,
  });
  await expect(companion).toBeVisible();
  await companion.click();

  await expect(page).toHaveURL(/\/en\/settings$/);
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await page.getByLabel("Maximum papers").fill("7");
  await page.getByLabel("Show companion").uncheck();
  await page.getByRole("button", { name: "Save settings" }).click();
  await expect(page.getByRole("status")).toHaveText("Settings saved");
  await expect(
    page.getByRole("button", { name: "Open settings" }),
  ).toBeVisible();

  await page.goto("/en");
  await page.getByRole("button", { name: "This research overrides" }).click();
  await expect(page.getByLabel("Maximum papers")).toHaveValue("7");
  await expect(
    page.getByRole("button", { name: "Open settings" }),
  ).toBeVisible();
});

test("keeps the companion inside the viewport after dragging and reload", async ({
  page,
}) => {
  await page.goto("/en");
  const companion = page.locator("[data-pet-state]");
  await expect(companion).toBeVisible();
  const before = await companion.boundingBox();
  if (!before) throw new Error("Companion did not have a bounding box");

  await page.mouse.move(
    before.x + before.width / 2,
    before.y + before.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(30, 30, { steps: 5 });
  await page.mouse.up();
  await page.reload();

  const after = await companion.boundingBox();
  if (!after) throw new Error("Companion disappeared after reload");
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Viewport is unavailable");
  expect(after.x).toBeGreaterThanOrEqual(0);
  expect(after.y).toBeGreaterThanOrEqual(0);
  expect(after.x + after.width).toBeLessThanOrEqual(viewport.width);
  expect(after.y + after.height).toBeLessThanOrEqual(viewport.height);
  expect(after.x).toBeLessThan(before.x - 20);
});

test.describe("reduced motion", () => {
  test("holds the system-mode companion on its poster frame", async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/en");
    const sprite = page.locator("[data-pet-frame]");
    await expect(sprite).toBeVisible();
    const initialFrame = await sprite.getAttribute("data-pet-frame");
    await page.waitForTimeout(650);
    await expect(sprite).toHaveAttribute("data-pet-frame", initialFrame ?? "0");
  });
});
