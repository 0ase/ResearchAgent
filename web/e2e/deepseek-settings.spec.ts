import { expect, test } from "@playwright/test";

test("requires a DeepSeek key on first use and replaces it from settings", async ({
  page,
}) => {
  let configured = false;
  const savedKeys: string[] = [];

  await page.route("**/api/v1/settings/deepseek", async (route) => {
    if (route.request().method() === "PUT") {
      const body = route.request().postDataJSON() as { api_key: string };
      savedKeys.push(body.api_key);
      configured = true;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provider: "deepseek",
        default_model: "deepseek-v4-flash",
        api_key_required: true,
        api_key_configured: configured,
      }),
    });
  });

  await page.goto("/en");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Configure a DeepSeek API key");
  await expect(
    dialog.getByRole("link", { name: "Open the DeepSeek API platform" }),
  ).toHaveAttribute("target", "_blank");

  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("DeepSeek API key").fill("sk-first-use");
  await dialog.getByRole("button", { name: "Save and continue" }).click();
  await expect(dialog).not.toBeVisible();

  await page.reload();
  await expect(page.getByRole("dialog")).not.toBeVisible();

  await page.goto("/en/settings");
  await expect(page.getByText("Configured", { exact: true })).toBeVisible();
  await page.getByLabel("Replace API key").fill("sk-replacement");
  await page.getByRole("button", { name: "Update API key" }).click();
  await expect(page.getByRole("status")).toHaveText("API key updated");
  expect(savedKeys).toEqual(["sk-first-use", "sk-replacement"]);
});
