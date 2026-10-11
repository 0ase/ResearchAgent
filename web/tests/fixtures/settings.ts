import type { Page } from '@playwright/test'

export const settingsSnapshot = {
  values: { default_model: 'fixture-model', base_url: 'https://api.example.org', screening_min_score: 70 },
  effective_values: { default_model: 'fixture-model' },
  secrets: { openai_api_key: { configured: true, saved: true, overridden: false, pending: false } },
  overridden_fields: [], pending_fields: [], restart_required: false, writable: true,
  runtime: { config_file: 'D:/BIGONE/.env' },
}

export async function mockSettingsRead(page: Page) {
  await page.route('**/api/settings', route => route.request().method() === 'GET'
    ? route.fulfill({ json: settingsSnapshot })
    : route.abort())
}
