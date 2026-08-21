import { defineConfig, devices } from "@playwright/test";

const chromeExecutable =
  process.env.PLAYWRIGHT_CHROME_PATH ??
  (process.platform === "win32"
    ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    : undefined);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    launchOptions: chromeExecutable
      ? { executablePath: chromeExecutable }
      : undefined,
  },
  projects: [
    {
      name: "chromium-1280",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: "chromium-1440",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
  webServer: {
    command:
      "powershell -NoProfile -ExecutionPolicy Bypass -File ../scripts/start_dev.ps1",
    url: "http://localhost:3000",
    reuseExistingServer: process.env.PW_REUSE_SERVER === "1",
    timeout: 120_000,
  },
});
