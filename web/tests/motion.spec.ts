import { expect, test, type Locator, type Page } from '@playwright/test'

async function advanceToPhase(page: Page, hint: Locator, phase: string) {
  for (let attempt = 0; attempt < 120; attempt++) {
    if (await hint.getAttribute('data-phase') === phase) return
    await page.clock.runFor(100)
  }
  throw new Error(`Prompt animation did not reach ${phase}`)
}

test('example questions decode and delete without becoming submitted input', async ({ page }) => {
  const apiRequests: string[] = []
  page.on('request', request => { if (request.url().includes('/api/')) apiRequests.push(request.url()) })
  await page.clock.install()
  await page.goto('/research?demo=1')
  await page.getByRole('button', { name: '新建研究', exact: true }).click()
  await page.clock.runFor(30)
  const input = page.getByRole('textbox', { name: '研究问题' })
  await expect(input).toBeFocused()
  await page.getByRole('heading', { name: '从一个问题开始。' }).click()
  const hint = page.locator('.prompt-animated-hint')
  await expect(hint).toBeVisible()
  await expect(hint).toHaveAttribute('aria-hidden', 'true')
  await page.clock.runFor(500)
  await expect(hint.locator('.prompt-cipher-glyph')).toHaveText(/^[A-Z0-9#$%&*+\-/<>\[\]{}]$/)
  await expect(input).toHaveValue('')
  await expect(page.getByRole('button', { name: '提交', exact: true })).toBeDisabled()
  await advanceToPhase(page, hint, 'holding')
  const firstQuestion = await hint.locator('.prompt-resolved-text').innerText()
  expect(firstQuestion).toBe('大语言模型如何辅助科研？')
  await page.clock.runFor(5000)
  await expect(hint.locator('.prompt-resolved-text')).toHaveText(firstQuestion)
  await expect(hint).toHaveAttribute('data-phase', 'holding')
  await advanceToPhase(page, hint, 'deleting')
  const deletingText = await hint.locator('.prompt-resolved-text').innerText()
  expect(firstQuestion.startsWith(deletingText)).toBe(true)
  expect(deletingText.length).toBeLessThan(firstQuestion.length)
  await page.clock.runFor(130)
  expect((await hint.locator('.prompt-resolved-text').innerText()).length).toBeLessThan(deletingText.length)
  await advanceToPhase(page, hint, 'holding')
  await expect(hint).toContainText('检索增强方法有哪些局限？')
  await expect(input).toHaveValue('')
  expect(apiRequests).toEqual([])
  await page.screenshot({ path: '../tmp/b1gone-motion-question.png' })

  await input.focus()
  await expect(hint).toHaveCount(0)
  await input.fill('我的实际研究问题')
  await page.getByRole('heading', { name: '从一个问题开始。' }).click()
  await page.clock.runFor(20000)
  await expect(input).toHaveValue('我的实际研究问题')
  await expect(hint).toHaveCount(0)
})

test('settings gear steps clockwise to 180 degrees and reverses to its origin on leave', async ({ page }) => {
  await page.goto('/research?demo=1')
  const hoverTarget = page.locator('.desktop-sidebar .settings-gear')
  const gear = hoverTarget.locator('.settings-gear-rotor')
  await expect(gear).toBeVisible()
  const sampleAngles = () => gear.evaluate(async element => {
    const samples: number[] = []
    const start = performance.now()
    await new Promise<void>(resolve => {
      function sample() {
        const matrix = new DOMMatrix(getComputedStyle(element).transform)
        const angle = Math.atan2(matrix.b, matrix.a) * 180 / Math.PI
        samples.push(Math.round(angle < -179.9 ? 180 : angle))
        if (performance.now() - start < 1300) requestAnimationFrame(sample)
        else resolve()
      }
      requestAnimationFrame(sample)
    })
    return samples
  })
  const timing = await gear.evaluate(element => ({ timing: getComputedStyle(element).transitionTimingFunction, duration: getComputedStyle(element).transitionDuration }))
  expect(timing.timing).toMatch(/^steps\(6(?:, end)?\)$/)
  expect(timing.duration).toBe('1s')
  const clockwise = sampleAngles()
  // Keep the mouse near an edge: the hover area must stay fixed as the icon turns.
  await hoverTarget.hover({ position: { x: 2, y: 2 } })
  const forward = await clockwise
  expect(forward[0]).toBe(0)
  expect(forward.at(-1)).toBe(180)
  expect(forward.some(angle => angle > 0 && angle < 180)).toBe(true)
  expect(forward.every((angle, index) => index === 0 || angle >= forward[index - 1])).toBe(true)
  // It stays at 180 degrees while hovered instead of repeating a full turn.
  expect((await sampleAngles()).every(angle => angle === 180)).toBe(true)
  const counterclockwise = sampleAngles()
  await page.getByRole('heading', { name: '研究综述', exact: true }).hover()
  const backward = await counterclockwise
  expect(backward[0]).toBe(180)
  expect(backward.at(-1)).toBe(0)
  expect(backward.some(angle => angle > 0 && angle < 180)).toBe(true)
  expect(backward.every((angle, index) => index === 0 || angle <= backward[index - 1])).toBe(true)
  await page.getByRole('button', { name: '设置', exact: true }).click()
  await expect(page.getByRole('dialog', { name: '原型设置' })).toBeVisible()
  await expect(page.locator('.prompt-animated-hint')).toHaveCount(0)
})

test('reduced motion keeps the static prompt and gear, including preference changes', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/research?demo=1')
  const input = page.getByRole('textbox', { name: '研究问题' })
  await expect(page.locator('.prompt-animated-hint')).toHaveCount(0)
  await expect(input).toHaveAttribute('placeholder', /继续追问/)
  const hoverTarget = page.locator('.desktop-sidebar .settings-gear')
  const gear = hoverTarget.locator('.settings-gear-rotor')
  await hoverTarget.hover()
  expect(await gear.evaluate(element => getComputedStyle(element).animationName)).toBe('none')
  expect(await gear.evaluate(element => getComputedStyle(element).transitionDuration)).toBe('0s')
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await expect(page.locator('.prompt-animated-hint')).toBeVisible()
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(page.locator('.prompt-animated-hint')).toHaveCount(0)
})
