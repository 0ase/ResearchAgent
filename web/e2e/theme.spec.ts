import { expect, test, type Page } from "@playwright/test";

const THEME_STORAGE_KEY = "research-agent.theme.v1";

const runningTask = {
  id: "theme-running-task",
  client_request_id: "theme-running-client",
  query: "Theme badge fixture",
  title: "Running theme fixture",
  status: "running",
  effective_locale: "en",
  current_stage: "search",
  last_sequence: 1,
  statistics: { papers_count: 1 },
  available_actions: ["cancel"],
  created_at: "2026-09-03T10:00:00+08:00",
  started_at: "2026-09-03T10:00:01+08:00",
  completed_at: null,
};

type ThemeBackendOptions = {
  active?: "ready" | "pending" | "task";
  history?: "none" | "task" | "error";
};

async function mockConfiguredApp(
  page: Page,
  options: ThemeBackendOptions = {},
) {
  await page.route("**/api/v1/settings/deepseek", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provider: "deepseek",
        default_model: "deepseek-v4-flash",
        api_key_required: false,
        api_key_configured: false,
      }),
    });
  });
  if (options.active === "task") {
    await page.route("**/api/v1/research/tasks/active", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(runningTask),
      });
    });
  } else if (options.active === "pending") {
    await page.route("**/api/v1/research/tasks/active", async () => {
      await new Promise<void>(() => undefined);
    });
  } else {
    await page.route("**/api/v1/research/tasks/active", async (route) => {
      await route.fulfill({ status: 204 });
    });
  }
  if (options.history === "task") {
    await page.route("**/api/v1/research/history*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([runningTask]),
      });
    });
  }
  if (options.history === "error") {
    await page.route("**/api/v1/research/history*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "INTERNAL_ERROR",
            message: "Theme alert fixture",
            retryable: true,
            request_id: "theme-test",
          },
        }),
      });
    });
  }
}
async function readThemeTokens(page: Page) {
  return page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    const pick = (name: string) => styles.getPropertyValue(name).trim();
    return {
      chrome: pick("--color-chrome"),
      page: pick("--color-page"),
      surface: pick("--color-surface"),
      surfaceSubtle: pick("--color-surface-subtle"),
      control: pick("--color-control"),
      controlHover: pick("--color-control-hover"),
      controlActive: pick("--color-control-active"),
      border: pick("--color-border"),
      borderStrong: pick("--color-border-strong"),
      text: pick("--color-text"),
      textMuted: pick("--color-text-muted"),
      textSubtle: pick("--color-text-subtle"),
      accent: pick("--color-primary"),
      accentHover: pick("--color-primary-hover"),
      accentActive: pick("--color-primary-active"),
      accentForeground: pick("--color-primary-foreground"),
      accentSubtle: pick("--color-primary-subtle"),
      accentBorder: pick("--color-primary-border"),
      info: pick("--color-info"),
      infoSubtle: pick("--color-info-subtle"),
      infoBorder: pick("--color-info-border"),
      success: pick("--color-success"),
      successSubtle: pick("--color-success-subtle"),
      successBorder: pick("--color-success-border"),
      warning: pick("--color-warning"),
      warningSubtle: pick("--color-warning-subtle"),
      warningBorder: pick("--color-warning-border"),
      error: pick("--color-error"),
      errorSubtle: pick("--color-error-subtle"),
      errorBorder: pick("--color-error-border"),
      tooltip: pick("--color-tooltip"),
      tooltipForeground: pick("--color-tooltip-foreground"),
      dialogOverlay: pick("--color-dialog-overlay"),
      skeleton: pick("--color-skeleton"),
      skeletonHighlight: pick("--color-skeleton-highlight"),
      colorScheme: styles.colorScheme,
      accentColor: styles.accentColor,
    };
  });
}

test("clean storage and a system dark preference still open in light", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await mockConfiguredApp(page);

  await page.goto("/en");
  await page.evaluate((key) => localStorage.removeItem(key), THEME_STORAGE_KEY);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.reload();

  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(
    page.getByRole("button", { name: "Switch to dark theme" }),
  ).toBeVisible();
  expect(await readThemeTokens(page)).toMatchObject({
    accent: "#2563eb",
    colorScheme: "light",
  });
  expect(errors).toEqual([]);
});

test("a persisted dark theme is applied before the first animation frame", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await mockConfiguredApp(page);

  await page.addInitScript((key) => {
    localStorage.setItem(key, "dark");
    requestAnimationFrame(() => {
      (
        window as unknown as { researchAgentThemeAtFirstFrame?: string | null }
      ).researchAgentThemeAtFirstFrame =
        document.documentElement.getAttribute("data-theme");
    });
  }, THEME_STORAGE_KEY);

  await page.goto("/en/history");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(
    page.getByRole("button", { name: "Switch to light theme" }),
  ).toBeVisible();

  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (
            window as unknown as {
              researchAgentThemeAtFirstFrame?: string | null;
            }
          ).researchAgentThemeAtFirstFrame,
      ),
    )
    .toBe("dark");
  expect(
    await page
      .locator("#research-agent-theme-init")
      .evaluate((element) => element.parentElement?.tagName),
  ).toBe("HEAD");

  const tokens = await readThemeTokens(page);
  expect(tokens).toMatchObject({
    chrome: "#181818",
    page: "#1f1f1f",
    surface: "#252526",
    surfaceSubtle: "#2a2a2b",
    control: "#313131",
    controlHover: "#383838",
    controlActive: "#2d2d2d",
    border: "#2b2b2b",
    borderStrong: "#3c3c3c",
    text: "#ccc",
    textMuted: "#a0a0a0",
    textSubtle: "#8c8c8c",
    accent: "#ffce47",
    accentHover: "#ffd666",
    accentActive: "#e0b22e",
    accentForeground: "#1f1f1f",
    accentSubtle: "#ffce471f",
    accentBorder: "#ffce4766",
    info: "#75beff",
    infoSubtle: "#75beff1f",
    infoBorder: "#75beff66",
    success: "#73c991",
    successSubtle: "#73c9911f",
    successBorder: "#73c99166",
    warning: "#f0a45d",
    warningSubtle: "#f0a45d1f",
    warningBorder: "#f0a45d66",
    error: "#f48771",
    errorSubtle: "#f487711f",
    errorBorder: "#f4877166",
    tooltip: "#2d2d30",
    tooltipForeground: "#f3f3f3",
    dialogOverlay: "#0009",
    skeleton: "#2d2d2d",
    skeletonHighlight: "#383838",
    colorScheme: "dark",
    accentColor: "rgb(255, 206, 71)",
  });
  expect(errors).toEqual([]);
});

test("workspace and history keep choice across refresh and route changes", async ({
  page,
}) => {
  await mockConfiguredApp(page);
  await page.goto("/en");
  await page.evaluate((key) => localStorage.removeItem(key), THEME_STORAGE_KEY);
  await page.reload();
  await expect(page.getByLabel("Research question")).toBeVisible();

  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("main")).toBeVisible();
  expect(
    await page.evaluate((key) => localStorage.getItem(key), THEME_STORAGE_KEY),
  ).toBe("dark");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.getByRole("link", { name: "History", exact: true }).click();
  await expect(page).toHaveURL(/\/en\/history$/);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(
    page.getByRole("heading", { name: "Research history", exact: true }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect(
    await page.evaluate((key) => localStorage.getItem(key), THEME_STORAGE_KEY),
  ).toBe("light");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("invalid stored theme safely falls back to light", async ({ page }) => {
  await mockConfiguredApp(page);
  await page.addInitScript(
    (key) => localStorage.setItem(key, "auto"),
    THEME_STORAGE_KEY,
  );
  await page.goto("/en");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(
    page.getByRole("button", { name: "Switch to dark theme" }),
  ).toBeVisible();
});

test("dark controls expose accent-colored primary, input focus, and tooltip", async ({
  page,
}) => {
  await mockConfiguredApp(page);
  await page.addInitScript(
    (key) => localStorage.setItem(key, "dark"),
    THEME_STORAGE_KEY,
  );
  await page.goto("/en");
  await expect(page.getByLabel("Research question")).toBeVisible();

  const primary = page.locator('[data-variant="primary"]').first();
  await expect(primary).toBeVisible();
  const primaryStyle = await primary.evaluate((element) => {
    const styles = getComputedStyle(element);
    return {
      backgroundColor: styles.backgroundColor,
      color: styles.color,
    };
  });
  expect(primaryStyle).toEqual({
    backgroundColor: "rgb(255, 206, 71)",
    color: "rgb(31, 31, 31)",
  });
  await primary.hover();
  await expect
    .poll(() =>
      primary.evaluate((element) => getComputedStyle(element).backgroundColor),
    )
    .toBe("rgb(255, 214, 102)");
  await page.mouse.down();
  await expect
    .poll(() =>
      primary.evaluate((element) => getComputedStyle(element).backgroundColor),
    )
    .toBe("rgb(224, 178, 46)");
  await page.mouse.up();

  const input = page.getByLabel("Research question");
  await expect(input).toBeVisible();
  expect(
    await input.evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
  ).toBe("rgb(49, 49, 49)");
  await input.focus();
  await expect
    .poll(() =>
      input.evaluate((element) => getComputedStyle(element).boxShadow),
    )
    .toContain("rgb(255, 206, 71)");

  const toggle = page.getByRole("button", { name: "Switch to light theme" });
  await toggle.hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toBeVisible();
  const tooltipStyle = await tooltip.evaluate((element) => {
    const styles = getComputedStyle(element);
    return {
      backgroundColor: styles.backgroundColor,
      color: styles.color,
    };
  });
  expect(tooltipStyle).toEqual({
    backgroundColor: "rgb(45, 45, 48)",
    color: "rgb(243, 243, 243)",
  });
});

test("active task CTA reuses primary hover, active, and focus-visible states", async ({
  page,
}) => {
  await mockConfiguredApp(page, { active: "task" });
  await page.addInitScript(
    (key) => localStorage.setItem(key, "dark"),
    THEME_STORAGE_KEY,
  );
  await page.goto("/en");

  const cta = page.getByRole("link", { name: "Return to research task" });
  await expect(cta).toBeVisible();
  expect(
    await cta.evaluate((element) => getComputedStyle(element).backgroundColor),
  ).toBe("rgb(255, 206, 71)");

  await cta.hover();
  await expect
    .poll(() =>
      cta.evaluate((element) => getComputedStyle(element).backgroundColor),
    )
    .toBe("rgb(255, 214, 102)");
  await page.mouse.down();
  await expect
    .poll(() =>
      cta.evaluate((element) => getComputedStyle(element).backgroundColor),
    )
    .toBe("rgb(224, 178, 46)");
  await page.mouse.move(0, 0);
  await page.mouse.up();

  for (let attempt = 0; attempt < 40; attempt += 1) {
    await page.keyboard.press("Tab");
    if (await cta.evaluate((element) => element === document.activeElement)) {
      break;
    }
  }
  await expect(cta).toBeFocused();
  await expect
    .poll(() => cta.evaluate((element) => getComputedStyle(element).boxShadow))
    .toContain("rgb(255, 206, 71)");
});

test("workspace regions do not overlap and remain reachable at supported widths", async ({
  page,
}) => {
  await mockConfiguredApp(page);
  await page.goto("/en");

  const regions = page.locator(
    'aside[aria-label="Task navigation"], main, aside[aria-label="Context panel"]',
  );
  await expect(regions).toHaveCount(3);

  const boxes = await regions.evaluateAll((elements) =>
    elements.map((element) => {
      const { bottom, height, left, right, top, width } =
        element.getBoundingClientRect();
      return { bottom, height, left, right, top, width };
    }),
  );
  for (const box of boxes) {
    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);
  }
  for (let index = 0; index < boxes.length; index += 1) {
    for (let next = index + 1; next < boxes.length; next += 1) {
      const first = boxes[index];
      const second = boxes[next];
      expect(
        first.right <= second.left ||
          second.right <= first.left ||
          first.bottom <= second.top ||
          second.bottom <= first.top,
      ).toBe(true);
    }
  }

  const dimensions = await page.evaluate(() => ({
    documentScrollWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  if (dimensions.viewportWidth <= 1024) {
    expect(dimensions.documentScrollWidth).toBeGreaterThan(
      dimensions.viewportWidth,
    );
    await page.evaluate(() => {
      window.scrollTo({ left: document.documentElement.scrollWidth, top: 0 });
    });
    const contextHeading = page.getByRole("heading", { name: "Context" });
    const evidenceTab = page.getByRole("tab", { name: "Evidence" });
    await expect(contextHeading).toBeInViewport();
    await expect(evidenceTab).toBeInViewport();
    const contextBox = await page
      .getByRole("complementary", { name: "Context panel" })
      .boundingBox();
    expect(contextBox).not.toBeNull();
    expect(contextBox!.x).toBeGreaterThanOrEqual(0);
    expect(contextBox!.x + contextBox!.width).toBeLessThanOrEqual(
      dimensions.viewportWidth,
    );
  } else {
    expect(dimensions.documentScrollWidth).toBeLessThanOrEqual(
      dimensions.viewportWidth,
    );
  }
});

test("dark links, active tab, and history badge use semantic colors", async ({
  page,
}) => {
  await mockConfiguredApp(page, { history: "task" });
  await page.addInitScript(
    (key) => localStorage.setItem(key, "dark"),
    THEME_STORAGE_KEY,
  );
  await page.goto("/en");
  await expect(page.getByLabel("Research question")).toBeVisible();

  const historyLink = page.getByRole("link", { name: "History" });
  expect(
    await historyLink.evaluate((element) => getComputedStyle(element).color),
  ).toBe("rgb(160, 160, 160)");

  const activeTab = page.getByRole("tab", { name: "Evidence" });
  expect(
    await activeTab.evaluate((element) => getComputedStyle(element).color),
  ).toBe("rgb(255, 214, 102)");

  await page.goto("/en/history");
  await expect(
    page.getByRole("heading", { name: "Research history", exact: true }),
  ).toBeVisible();
  const newResearchLink = page.getByRole("link", { name: "New research" });
  expect(
    await newResearchLink.evaluate(
      (element) => getComputedStyle(element).color,
    ),
  ).toBe("rgb(255, 206, 71)");

  const runningBadge = page
    .locator("article")
    .first()
    .getByText("Running", { exact: true });
  await expect(runningBadge).toBeVisible();
  expect(
    await runningBadge.evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
  ).toContain("255, 206, 71");
});

test("dark skeleton and alert keep their semantic two-tone and status colors", async ({
  page,
}) => {
  await mockConfiguredApp(page, {
    active: "pending",
    history: "error",
  });
  await page.addInitScript(
    (key) => localStorage.setItem(key, "dark"),
    THEME_STORAGE_KEY,
  );
  await page.goto("/en");

  const skeleton = page.locator(".skeleton").first();
  await expect(skeleton).toBeVisible();
  const skeletonImage = await skeleton.evaluate(
    (element) => getComputedStyle(element).backgroundImage,
  );
  expect(skeletonImage).toContain("rgb(45, 45, 45)");
  expect(skeletonImage).toContain("rgb(56, 56, 56)");

  await page.goto("/en/history");
  const errorText = page.getByText("Unable to load research history.");
  await expect(errorText).toBeVisible({ timeout: 15_000 });
  const alert = page.locator('[role="alert"]', {
    hasText: "Unable to load research history.",
  });
  expect(
    await alert.evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
  ).toBe("rgba(244, 135, 113, 0.12)");
});

test("dark DeepSeek gate dialog uses surface tokens and keeps the control accessible", async ({
  page,
}) => {
  await page.addInitScript(
    (key) => localStorage.setItem(key, "dark"),
    THEME_STORAGE_KEY,
  );
  await page.route("**/api/v1/settings/deepseek", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provider: "deepseek",
        default_model: "deepseek-v4-flash",
        api_key_required: true,
        api_key_configured: false,
      }),
    });
  });
  await page.goto("/en");

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  expect(
    await dialog.evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
  ).toBe("rgb(37, 37, 38)");
  await expect(
    dialog.getByRole("button", { name: "Switch to light theme" }),
  ).toBeVisible();
});
test("404 and DeepSeek-ready entry points expose the theme control", async ({
  page,
}) => {
  await mockConfiguredApp(page);
  await page.goto("/en/this-page-does-not-exist");
  await expect(
    page.getByRole("heading", { name: /could not be found/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Switch to dark theme" }),
  ).toBeVisible();

  await page.goto("/en/settings");
  await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Switch to dark theme" }),
  ).toBeVisible();
});
