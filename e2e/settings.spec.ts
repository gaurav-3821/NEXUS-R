import { test, expect } from '@playwright/test'

test.describe('Settings Pages', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
  })

  test('should display all settings categories', async ({ page }) => {
    const categories = [
      'General',
      'Providers',
      'Models',
      'Memory',
      'Appearance',
      'Advanced',
    ]
    for (const category of categories) {
      await expect(page.locator(`text=${category}`).first()).toBeVisible()
    }
  })

  test('should update API key', async ({ page }) => {
    await page.goto('/settings/providers')
    const input = page.locator('[data-testid="api-key-input"]')
    await input.fill('sk-test-key-12345')
    await page.click('[data-testid="save-api-key"]')
    await expect(page.locator('text=API key saved')).toBeVisible()
  })

  test('should change model provider', async ({ page }) => {
    await page.goto('/settings/models')
    await page.selectOption('[data-testid="provider-select"]', 'openrouter')
    await expect(page.locator('[data-testid="model-list"]')).toBeVisible()
  })

  test('should toggle memory persistence', async ({ page }) => {
    await page.goto('/settings/memory')
    const toggle = page.locator('[data-testid="memory-persistence-toggle"]')
    const isChecked = await toggle.isChecked()
    await toggle.click()
    await expect(page.locator('text=Memory settings updated')).toBeVisible()
  })
})
