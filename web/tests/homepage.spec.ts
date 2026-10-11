import { expect, test } from '@playwright/test'

test('homepage keeps the selected composition, readable labels and local documentation', async ({ page }) => {
  const errors: string[] = []
  const apiRequests: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => { if (request.url().includes('/api/') || request.url().endsWith('/health')) apiRequests.push(request.url()) })
  await page.goto('/?demo=1')
  await page.evaluate(() => document.fonts.ready)
  await expect(page.getByRole('heading', { name: 'B1GONE 研究助手', exact: true })).toBeVisible()
  const nav = page.getByRole('navigation', { name: '首页导航' })
  await expect(nav.getByRole('button')).toHaveText(['文档', '设置'])
  await expect(nav.getByRole('link', { name: '在 GitHub 查看 B1GONE 项目' })).toHaveAttribute('href', 'https://github.com/0ase/ResearchAgent')
  await expect(nav.getByRole('link')).toHaveAttribute('rel', 'noopener noreferrer')
  await expect(page.getByRole('textbox', { name: '研究问题', exact: true })).toHaveValue('')
  await expect(page.getByRole('button', { name: '开始研究', exact: true })).toBeDisabled()

  const geometry = await page.evaluate(() => {
    const box = (selector: string) => document.querySelector(selector)!.getBoundingClientRect()
    const intro = box('.home-introduction p')
    const firstNode = box('.home-pipeline li')
    const beam = box('.home-input-beam')
    const outputs = [...document.querySelectorAll('.home-question-rays text')].map(element => element.getBoundingClientRect().right)
    return { introBottom: intro.bottom, nodeTop: firstNode.top, beamY: beam.top, outputs, width: window.innerWidth, overflow: document.documentElement.scrollWidth > window.innerWidth }
  })
  expect(geometry.beamY).toBeGreaterThan(geometry.introBottom + 8)
  expect(geometry.beamY).toBeLessThan(geometry.nodeTop - 8)
  expect(geometry.outputs.every(right => right < geometry.width)).toBe(true)
  expect(geometry.overflow).toBe(false)
  await page.screenshot({ path: '../tmp/b1gone-homepage-desktop.png' })
  await nav.getByRole('button', { name: '文档', exact: true }).click()
  await expect(page.getByRole('dialog', { name: '使用文档' })).toContainText('研究过程')
  await page.keyboard.press('Escape')
  await expect(nav.getByRole('button', { name: '文档', exact: true })).toBeFocused()
  expect(apiRequests).toEqual([])
  expect(errors).toEqual([])
})

test('homepage reuses settings and preserves the research across page navigation', async ({ page }) => {
  await page.goto('/?demo=1')
  const input = page.getByRole('textbox', { name: '研究问题', exact: true })
  await input.fill('  比较 Transformer 的高效变体  ')
  await page.getByRole('button', { name: '设置', exact: true }).click()
  await page.getByLabel('目标阅读数量').selectOption('5')
  await page.getByRole('button', { name: '完成', exact: true }).click()
  await expect(input).toHaveValue('  比较 Transformer 的高效变体  ')
  await page.getByRole('button', { name: '开始研究', exact: true }).click()
  await expect(page).toHaveURL('/research?demo=1')
  await expect(page.locator('.user-question')).toContainText('比较 Transformer 的高效变体')
  await expect(page.getByRole('button', { name: '停止', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '返回首页', exact: true }).click()
  await expect(page).toHaveURL('/?demo=1')
  await page.goBack()
  await expect(page).toHaveURL('/research?demo=1')
  await expect(page.locator('.user-question')).toContainText('比较 Transformer 的高效变体')
  await expect(page.locator('.desktop-sidebar .history-item').filter({ hasText: '比较 Transformer 的高效变体' })).toHaveCount(1)
  await page.getByRole('button', { name: '停止', exact: true }).click()
  await page.goForward()
  await expect(page).toHaveURL('/?demo=1')
})

test('homepage sends only the actual user question to the existing research endpoint', async ({ page }) => {
  const submitted: unknown[] = []
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/api/research/history?*', route => route.fulfill({ json: [] }))
  await page.route('**/api/research/stream', route => {
    submitted.push(route.request().postDataJSON())
    return route.fulfill({ contentType: 'text/event-stream', body: 'data: {"event":"error","message":"测试用例返回的错误","error_id":"homepage-test-trace"}\n\n' })
  })
  await page.goto('/')
  const input = page.getByRole('textbox', { name: '研究问题', exact: true })
  await input.fill('   ')
  await input.press('Enter')
  expect(submitted).toEqual([])
  await input.fill('我的实际问题')
  await input.press('Shift+Enter')
  await expect(input).toHaveValue('我的实际问题\n')
  expect(submitted).toEqual([])
  await input.fill('我的实际问题')
  // Enter used to confirm an IME composition must not start a research request.
  await input.dispatchEvent('keydown', { key: 'Enter', isComposing: true })
  expect(submitted).toEqual([])
  await input.press('Enter')
  await expect(page).toHaveURL('/research')
  await expect(page.getByRole('alert')).toContainText('homepage-test-trace')
  expect(submitted).toEqual([{ query: '我的实际问题', max_papers: 15 }])
  await expect(page.locator('.user-question')).toContainText('我的实际问题')
})

test('homepage real settings reuse the masked configuration view', async ({ page }) => {
  const calls: string[] = []
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/api/research/history?*', route => route.fulfill({ json: [] }))
  await page.route('**/api/settings', route => {
    calls.push(route.request().method())
    return route.fulfill({ json: { values: {}, effective_values: {}, secrets: { openai_api_key: { configured: true, saved: true, overridden: false, pending: false } }, overridden_fields: [], pending_fields: [], restart_required: false, writable: true, runtime: {} } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: '设置', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '研究设置' })
  await expect(dialog).toContainText('当前已配置')
  await expect(dialog.getByLabel('OpenAI / 兼容密钥')).toHaveValue('')
  await page.keyboard.press('Escape')
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every(method => method === 'GET')).toBe(true)
})

test('homepage adapts its illustration and controls to small screens without overflow', async ({ page }) => {
  for (const width of [390, 320, 900]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/?demo=1')
    await page.evaluate(() => document.fonts.ready)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await expect(page.locator('.home-mobile-example')).toBeVisible()
    await expect(page.locator('.home-mobile-subquestions li')).toHaveCount(4)
    await expect(page.getByRole('textbox', { name: '研究问题' })).toBeVisible()
    const nav = page.getByRole('navigation', { name: '首页导航' })
    const github = (await nav.getByRole('link').boundingBox())!
    expect(github.width).toBeGreaterThanOrEqual(44)
    expect(github.x + github.width).toBeLessThanOrEqual(width)
    if (width === 390) await page.screenshot({ path: '../tmp/b1gone-homepage-mobile.png', fullPage: true })
  }
})
