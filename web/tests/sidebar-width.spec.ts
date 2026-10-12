import { expect, test } from '@playwright/test'

test('left sidebar supports dragging, cancelling, keyboard resizing and restoring its width', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/research?demo=1')
  await page.evaluate(() => document.fonts.ready)
  const sidebar = page.locator('.desktop-sidebar')
  const workspace = page.locator('.workspace')
  const papers = page.locator('.paper-panel')
  const handle = page.getByRole('separator', { name: '调整研究记录栏宽度' })
  const originalWidth = (await sidebar.boundingBox())!.width
  const originalWorkspace = (await workspace.boundingBox())!.width
  const originalPapers = (await papers.boundingBox())!.width
  await page.getByRole('textbox', { name: '研究问题' }).fill('调宽时保留未提交的问题')

  let grip = (await handle.boundingBox())!
  await page.mouse.move(grip.x + grip.width / 2, 230)
  await page.mouse.down()
  await page.mouse.move(grip.x + grip.width / 2 + 90, 230, { steps: 10 })
  await page.mouse.up()
  await expect.poll(async () => (await sidebar.boundingBox())!.width).toBeCloseTo(originalWidth + 90, 0)
  expect((await workspace.boundingBox())!.width).toBeCloseTo(originalWorkspace - 90, 0)
  expect((await papers.boundingBox())!.width).toBeCloseTo(originalPapers, 0)
  await expect(page.getByRole('textbox', { name: '研究问题' })).toHaveValue('调宽时保留未提交的问题')

  const committedWidth = (await sidebar.boundingBox())!.width
  grip = (await handle.boundingBox())!
  await page.mouse.move(grip.x + grip.width / 2, 230)
  await page.mouse.down()
  await page.mouse.move(grip.x + grip.width / 2 - 60, 230, { steps: 6 })
  await page.keyboard.press('Escape')
  await page.mouse.up()
  expect((await sidebar.boundingBox())!.width).toBeCloseTo(committedWidth, 0)
  await expect(page.locator('.app-shell')).not.toHaveClass(/is-resizing-sidebar/)

  await handle.press('ArrowLeft')
  expect((await sidebar.boundingBox())!.width).toBeCloseTo(committedWidth - 16, 0)
  await handle.press('Home')
  expect((await sidebar.boundingBox())!.width).toBe(220)
  await handle.press('End')
  expect((await sidebar.boundingBox())!.width).toBe(480)
  await handle.press('Shift+ArrowLeft')
  expect((await sidebar.boundingBox())!.width).toBe(440)
  await expect(handle).toHaveAttribute('aria-valuenow', '440')
  await page.screenshot({ path: '../tmp/b1gone-left-sidebar-width.png' })

  await page.getByRole('button', { name: '收起侧边栏', exact: true }).click()
  expect((await sidebar.boundingBox())!.width).toBe(56)
  await expect(handle).toHaveCount(0)
  await page.getByRole('button', { name: '展开侧边栏', exact: true }).click()
  expect((await sidebar.boundingBox())!.width).toBe(440)
  await expect(page.getByRole('textbox', { name: '研究问题' })).toHaveValue('调宽时保留未提交的问题')
  await expect(page.getByRole('button', { name: '收起侧边栏', exact: true })).toBeFocused()

  await page.getByRole('button', { name: '返回首页', exact: true }).click()
  await page.getByRole('button', { name: '开始研究', exact: true }).click()
  await expect(page.getByRole('heading', { name: '从一个问题开始。' })).toBeVisible()
  expect((await sidebar.boundingBox())!.width).toBe(440)
  expect(errors).toEqual([])
})

test('left and right widths preserve report space when panels reopen and the viewport shrinks', async ({ page }) => {
  await page.goto('/research?demo=1')
  const sidebar = page.locator('.desktop-sidebar')
  const workspace = page.locator('.workspace')
  const left = page.getByRole('separator', { name: '调整研究记录栏宽度' })
  const right = page.getByRole('separator', { name: '调整研究文献栏宽度' })
  await right.press('End')
  await left.press('End')
  await expect.poll(async () => (await workspace.boundingBox())!.width).toBeGreaterThanOrEqual(419)
  await page.getByRole('button', { name: '关闭研究文献' }).click()
  await left.press('End')
  expect((await sidebar.boundingBox())!.width).toBe(480)
  await page.getByRole('button', { name: '研究文献 · 15' }).click()
  await expect.poll(async () => (await workspace.boundingBox())!.width).toBeGreaterThanOrEqual(419)

  await page.setViewportSize({ width: 1100, height: 800 })
  await expect.poll(async () => (await workspace.boundingBox())!.width).toBeGreaterThanOrEqual(419)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('button', { name: '关闭研究文献' }).click()
  await expect.poll(async () => (await sidebar.boundingBox())!.width).toBe(480)
  await page.setViewportSize({ width: 701, height: 800 })
  await expect.poll(async () => (await workspace.boundingBox())!.width).toBeGreaterThanOrEqual(419)

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(left).not.toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('button', { name: '打开研究记录', exact: true }).click()
  const drawer = page.getByRole('dialog', { name: '研究记录', exact: true })
  await expect(drawer).toBeVisible()
  expect((await drawer.boundingBox())!.width).toBeLessThanOrEqual(390)
  await page.getByRole('button', { name: '关闭研究记录', exact: true }).click()
  await page.setViewportSize({ width: 1672, height: 941 })
  await expect.poll(async () => (await sidebar.boundingBox())!.width).toBe(480)
})
