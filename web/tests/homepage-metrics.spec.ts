import { expect, test } from '@playwright/test'

const metrics = [
  ['latency_p50', 'P50 完成耗时', 120, 'seconds', 6], ['latency_p99', 'P99 完成耗时', 450, 'seconds', 6],
  ['mean_completion_seconds', '平均完成耗时', 210, 'seconds', 6], ['mean_llm_tokens', '平均 LLM token', null, 'tokens', 0],
  ['rag_hit_rate', 'RAG Hit@K', null, '%', 0], ['task_completion_rate', '任务完成率', 75, '%', 8],
].map(([id, label, value, unit, samples]) => ({ id, label, value, unit, samples, status: value === null ? 'unavailable' : 'available', definition: '测试统计口径', reason: value === null ? '缺少完整 usage 或金标准记录' : '', numerator: null, denominator: null }))
const snapshot = { schema_version: 1, generated_at: '2026-10-11T13:00:00+00:00',
  population: { started: 9, completed: 6, failed: 2, cancelled: 0, incomplete: 1, timed_successes: 6, complete_usage_runs: 0, labeled_runs: 0 },
  window: { start: '2026-10-08T00:00:00+00:00', end: '2026-10-11T12:00:00+00:00' },
  groups: [{ id: 'latency', label: '耗时', metrics }],
  stages: [{ stage: 'read', started: 8, completed: 6, failed: 1, degraded: 1, mean_seconds: 100, p50_seconds: 95, p95_seconds: 130, p99_seconds: 140 }],
  notes: ['小样本 P99 不能作为生产 SLA。'] }

test('homepage metrics remain below the first screen, show observed values and N/A, and preserve the research entry', async ({ page }) => {
  const apiRequests: string[] = []
  let refreshes = 0
  page.on('request', request => { if (request.url().includes('/api/')) apiRequests.push(request.url()) })
  await page.route('**/metrics/summary.json', route => { refreshes++; return route.fulfill({ json: snapshot }) })
  await page.goto('/?demo=1')
  const region = page.getByRole('region', { name: '运行与评测' })
  await expect(region).toContainText('9 次研究启动')
  const top = await region.evaluate(element => element.getBoundingClientRect().top)
  expect(top).toBeGreaterThanOrEqual(await page.evaluate(() => window.innerHeight - 1))
  await region.scrollIntoViewIfNeeded()
  await expect(region.locator('[data-metric-id=latency_p50] dd')).toContainText('120')
  await expect(region.locator('[data-metric-id=mean_llm_tokens] dd')).toHaveText('N/A')
  await expect(region.locator('[data-metric-id=rag_hit_rate]')).toContainText('缺少完整 usage 或金标准记录')
  await region.getByRole('button', { name: '刷新读数', exact: true }).click()
  await expect.poll(() => refreshes).toBeGreaterThanOrEqual(2)
  await page.setViewportSize({ width: 320, height: 844 })
  await region.getByText('阶段性能 · 完成耗时与失败记录', { exact: true }).click()
  await expect(region.getByRole('table')).toContainText('read')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('button', { name: '开始研究', exact: true }).click()
  await expect(page).toHaveURL('/research?demo=1')
  await expect(page.getByRole('heading', { name: '从一个问题开始。' })).toBeVisible()
  expect(apiRequests).toEqual([])
})

test('missing or malformed metric snapshots never show fabricated zero statistics', async ({ page }) => {
  await page.route('**/metrics/summary.json', route => route.fulfill({ status: 404 }))
  await page.goto('/?demo=1')
  const region = page.getByRole('region', { name: '运行与评测' })
  await expect(region).toContainText('尚无可读取的统计快照')
  await expect(region.locator('.metric-readout')).toHaveCount(0)
  await page.route('**/metrics/summary.json', route => route.fulfill({ json: { ...snapshot, groups: [{ id: 'bad', label: 'bad', metrics: [{ ...metrics[0], value: 'not a number' }] }] } }))
  await region.getByRole('button', { name: '刷新读数', exact: true }).click()
  await expect(region).toContainText('尚无可读取的统计快照')
  await expect(region.locator('.metric-readout')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '开始研究', exact: true })).toBeEnabled()
})
