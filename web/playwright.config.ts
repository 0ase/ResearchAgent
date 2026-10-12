import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: '../tmp/b1gone-test-results',
  use: { channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', baseURL: 'http://127.0.0.1:5173', viewport: { width: 1672, height: 941 }, trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
})
