import { expect, test, type Page } from '@playwright/test'

const papers = [
  { source_id: 'A', title: '实际论文 A', authors: ['Zhang'], published_date: '2024-01-01', venue: 'Journal A', abstract: '论文 A 的真实摘要', pdf_url: 'https://example.org/a.pdf' },
  { source_id: 'B', title: '实际论文 B', authors: ['Li'], published_date: '2023-01-01', venue: 'Journal B', abstract: '论文 B 的摘要', doi: '10.1234/b' },
  { source_id: 'C', title: '入选但阅读失败的论文 C', authors: [], abstract: '' },
]
const result = {
  final_answer: '# 真实研究综述\n\n研究共识来自证据 [Source A]。\n\n|方法|证据|\n|---|---|\n|比较|结果|\n\n## 参考文献\n\n[Source B] 仅出现在参考文献列表。',
  papers, selected_papers: papers, paper_insights: [{ source: 'A', answer: 'A 的阅读结果' }, { source: 'B', answer: 'B 的阅读结果' }, { source: 'C', answer: '' }],
  agent_trace: [{ next_agent: 'retrieval', objective: '检索相关证据', reason: '需要补足证据' }],
  analysis: { agreements: [{}], contradictions: [], gaps: [{}] }, warnings: [], request_id: 'request-real-1',
}
const frame = (event: object) => `data: ${JSON.stringify(event)}\n\n`
const stream = [
  { event: 'agent', next_agent: 'retrieval', objective: '准备检索', request_id: 'request-real-1' },
  { event: 'stage', stage: 'orchestrate', sub_queries: ['子问题甲', '子问题乙'] },
  { event: 'stage', stage: 'search', total: 80, arxiv: 30, s2: 50 },
  { event: 'stage', stage: 'search', total: 93, arxiv: 40, s2: 53 },
  { event: 'stage', stage: 'filter', count: 3, summary: { evaluated_count: 10 } },
  { event: 'stage', stage: 'read', papers_read: 2 },
  { event: 'done', ...result, session_id: 'server-session-1' },
].map(frame).join('')

async function fixture(page: Page, options: { history?: boolean; streamBody?: string } = {}) {
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/research/history') return route.fulfill({ json: options.history ? [{ session_id: 'server-session-1', query: '历史研究问题', created_at: '2026-10-10T09:00:00', papers_count: 93 }] : [] })
    if (path === '/api/research/stream') return route.fulfill({ contentType: 'text/event-stream', body: options.streamBody ?? stream })
    if (path === '/api/research/server-session-1') return route.fulfill({ json: { session_id: 'server-session-1', query: '历史研究问题', created_at: '2026-10-10T09:00:00', result } })
    if (path.endsWith('/messages')) return route.fulfill({ json: [{ message_id: 'server-session-1:initial:user', role: 'user', content: '历史研究问题', citations: [] }, { message_id: 'server-session-1:initial:assistant', role: 'assistant', content: result.final_answer, citations: [] }] })
    throw new Error(`Unexpected API request: ${path}`)
  })
}

test('real research uses returned Markdown, repeated records and actual reading/citation counts', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await fixture(page)
  await page.goto('/')
  await expect(page.getByText('后端已连接', { exact: true })).toBeVisible()
  await page.getByRole('textbox', { name: '研究问题' }).fill('研究当前问题')
  await page.getByRole('button', { name: '提交', exact: true }).click()
  await expect(page.getByRole('heading', { name: '真实研究综述' })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
  await page.getByRole('button', { name: '研究过程' }).click()
  await expect(page.locator('.stage-title').filter({ hasText: '搜索相关文献' })).toHaveCount(2)
  await expect(page.locator('.terminal-output')).toContainText(['子问题甲', '80', '93'])
  await expect(page.locator('.stage-status').filter({ hasText: '结果已返回' })).toHaveCount(5)
  await page.getByRole('button', { name: '查看引用文献 A', exact: true }).click()
  const panel = page.locator('.paper-panel')
  await expect(panel).toContainText('已阅读 2 · 报告引用 1')
  await expect(panel).toContainText('实际论文 B')
  await expect(panel).not.toContainText('论文 C')
  await expect(panel.locator('[data-paper-id="A"]')).toHaveClass(/paper-highlighted/)
  await expect(panel.locator('[data-paper-id="A"] a')).toHaveAttribute('href', 'https://example.org/a.pdf')
  await expect(panel.locator('[data-paper-id="B"] a')).toHaveAttribute('href', 'https://doi.org/10.1234/b')
  await page.screenshot({ path: '../tmp/b1gone-api-completed.png' })
  expect(errors).toEqual([])
})

test('history loads report and followup retries retain the same message id', async ({ page }) => {
  await fixture(page, { history: true })
  const ids: string[] = []
  await page.route('**/api/research/server-session-1/chat', route => {
    ids.push(route.request().postDataJSON().message_id)
    return ids.length === 1
      ? route.fulfill({ status: 503, json: { error: { message: '模型暂时不可用', error_id: 'followup-error-1' } } })
      : route.fulfill({ json: { session_id: 'server-session-1', answer: '来自当前文献的回答 [Source A]', citations: ['A'] } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: /历史研究问题/ }).click()
  await expect(page.getByRole('heading', { name: '真实研究综述' })).toBeVisible()
  await expect(page.locator('.chat-message')).toHaveCount(0)
  await page.getByRole('textbox', { name: '研究问题' }).fill('证据的局限是什么？')
  await page.getByRole('button', { name: '提交', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('followup-error-1')
  await page.getByRole('button', { name: '重试追问' }).click()
  await expect(page.locator('.chat-assistant')).toContainText('来自当前文献的回答')
  await expect(page.locator('.chat-user')).toHaveCount(1)
  expect(ids).toHaveLength(2)
  expect(ids[1]).toBe(ids[0])
})

test('stream errors retain backend tracking ids and incomplete streams never show a report', async ({ page }) => {
  await fixture(page, { streamBody: frame({ event: 'error', message: '分析生成达到长度上限', error_id: 'analysis-error-9', request_id: 'request-9' }) })
  await page.goto('/')
  await page.getByRole('textbox', { name: '研究问题' }).fill('分析失败用例')
  await page.getByRole('button', { name: '提交', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('analysis-error-9')
  await expect(page.getByRole('alert')).toContainText('request-9')
  await expect(page.getByRole('article', { name: '研究综述' })).toHaveCount(0)
  await page.route('**/api/research/stream', route => route.fulfill({ contentType: 'text/event-stream', body: frame({ event: 'stage', stage: 'search', total: 80 }) }))
  await page.getByRole('button', { name: '重试研究' }).click()
  await expect(page.getByRole('alert')).toContainText('连接提前断开')
})

test('SSE decoder handles single-byte Chinese chunks, CRLF, multiline data and trailing done', async ({ page }) => {
  await fixture(page)
  await page.goto('/')
  const outcome = await page.evaluate(async () => {
    const modulePath = '/src/services/apiClient.ts'
    const { readEventStream } = await import(modulePath)
    const bytes = new TextEncoder().encode('data: {"event":"stage",\r\ndata: "preview":"中文分块"}\r\n\r\n: heartbeat\r\n\r\ndata: {"event":"done"}')
    const body = new ReadableStream({ start(controller) { for (const byte of bytes) controller.enqueue(new Uint8Array([byte])); controller.close() } })
    const events: Array<Record<string, unknown>> = []
    await readEventStream(new Response(body), (event: Record<string, unknown>) => events.push(event))
    return events
  })
  expect(outcome).toEqual([{ event: 'stage', preview: '中文分块' }, { event: 'done' }])
})

test('historical direct source ids and DOI aliases match only known read papers', async ({ page }) => {
  await fixture(page)
  await page.goto('/')
  const outcome = await page.evaluate(async () => {
    const modulePath = '/src/services/researchAdapter.ts'
    const { resultPapers } = await import(modulePath)
    const source = { final_answer: '# 旧报告\n\n证据 [arxiv:1234.56789] [10.1234/test] [arxiv:unknown]。\n\n## 参考文献\n\n[arxiv:only-reference]',
      papers: [{ source_id: 'arxiv:1234.56789', title: 'A' }, { source_id: 'crossref:10.1234/test', title: 'B', doi: '10.1234/test' }, { source_id: 'arxiv:only-reference', title: 'C' }],
      paper_insights: [{ source: 'arxiv:1234.56789', answer: 'A' }, { source: 'crossref:10.1234/test', answer: 'B' }, { source: 'arxiv:only-reference', answer: 'C' }] }
    const result = resultPapers(source)
    return { cited: result.papers.filter((paper: { cited: boolean }) => paper.cited).map((paper: { id: string }) => paper.id), incomplete: result.citationIncomplete }
  })
  expect(outcome).toEqual({ cited: ['arxiv:1234.56789', 'crossref:10.1234/test'], incomplete: true })
})

test('settings show masked status and send only changed fields and explicit secret edits', async ({ page }) => {
  await fixture(page)
  const snapshot = { values: { default_model: 'old-model', base_url: 'https://api.example.org', screening_min_score: 70 }, effective_values: { default_model: 'old-model' }, secrets: { openai_api_key: { configured: true, saved: true, overridden: false, pending: false } }, overridden_fields: [], pending_fields: [], restart_required: false, writable: true, runtime: { config_file: 'D:/BIGONE/.env' } }
  let update: Record<string, unknown> | undefined
  await page.route('**/api/settings', route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: snapshot })
    expect(route.request().headers()['x-b1gone-config']).toBe('local')
    update = route.request().postDataJSON()
    return route.fulfill({ json: { ...snapshot, values: { ...snapshot.values, default_model: 'next-model' }, pending_fields: ['default_model', 'openai_api_key'], restart_required: true } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: '设置', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '研究设置' })
  await expect(dialog).toContainText('当前已配置')
  await expect(dialog.getByLabel('OpenAI / 兼容密钥')).toHaveValue('')
  await dialog.getByLabel('主模型', { exact: true }).fill('next-model')
  await dialog.getByLabel('OpenAI / 兼容密钥').fill('test-only-private-value')
  await dialog.getByRole('button', { name: '保存配置' }).click()
  await expect(dialog.getByRole('status')).toContainText('重启后端')
  expect(update).toEqual({ values: { default_model: 'next-model' }, secrets: { openai_api_key: 'test-only-private-value' }, clear_secrets: [] })
  await expect(dialog.getByLabel('OpenAI / 兼容密钥')).toHaveValue('')
  expect(await page.evaluate(() => Object.values(localStorage))).not.toContain('test-only-private-value')
  await page.screenshot({ path: '../tmp/b1gone-api-settings.png' })
})

test('stop aborts the connection without claiming server cancellation confirmation', async ({ page }) => {
  await fixture(page)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/research/stream', async route => { await gate; await route.abort().catch(() => {}) })
  await page.goto('/')
  await page.getByRole('textbox', { name: '研究问题' }).fill('停止研究用例')
  const requested = page.waitForRequest('**/api/research/stream')
  await page.getByRole('button', { name: '提交', exact: true }).click()
  await requested
  await page.getByRole('button', { name: '停止', exact: true }).click()
  release()
  await expect(page.getByRole('heading', { name: '已停止接收研究结果' })).toBeVisible()
  await expect(page.locator('.cancelled-panel')).toContainText('未取得服务器取消确认')
  await expect(page.getByRole('article', { name: '研究综述' })).toHaveCount(0)
})
