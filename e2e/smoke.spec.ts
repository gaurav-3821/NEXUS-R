import { test, expect } from '@playwright/test'

test.describe('NEXUS-R Smoke Tests', () => {
  test('should display splash screen on first visit', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('[data-testid="splash-screen"]')).toBeVisible()
    await expect(page.locator('text=NEXUS-R')).toBeVisible()
  })

  test('should navigate to chat interface', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="chat-interface"]', { timeout: 10000 })
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible()
  })

  test('should send a message and receive response', async ({ page }) => {
    await page.goto('/chat')
    const input = page.locator('[data-testid="chat-input"]')
    await input.fill('Hello, this is a test message')
    await page.locator('[data-testid="send-button"]').click()
    await expect(page.locator('[data-testid="user-message"]')).toContainText('Hello, this is a test message')
    await page.waitForSelector('[data-testid="assistant-message"]', { timeout: 30000 })
    await expect(page.locator('[data-testid="assistant-message"]')).toBeVisible()
  })

  test('should toggle sidebar', async ({ page }) => {
    await page.goto('/')
    const sidebar = page.locator('[data-testid="sidebar"]')
    const toggle = page.locator('[data-testid="sidebar-toggle"]')
    await expect(sidebar).toBeVisible()
    await toggle.click()
    await expect(sidebar).not.toBeVisible()
  })

  test('should navigate to settings', async ({ page }) => {
    await page.goto('/')
    await page.click('[data-testid="settings-link"]')
    await expect(page).toHaveURL(/.*settings/)
    await expect(page.locator('text=Settings')).toBeVisible()
  })

  test('should switch themes', async ({ page }) => {
    await page.goto('/settings/appearance')
    await page.click('[data-testid="theme-dark"]')
    const html = page.locator('html')
    await expect(html).toHaveClass(/dark/)
  })
})
