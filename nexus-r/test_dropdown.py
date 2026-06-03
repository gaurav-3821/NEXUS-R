import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on('console', lambda msg: print('CONSOLE:', msg.text))
        
        print('Navigating...')
        await page.goto('http://127.0.0.1:5173/settings/models')
        
        print('Waiting for load...')
        await page.wait_for_selector('h3:has-text("Models")', timeout=10000)
        await page.wait_for_timeout(2000)

        print('Finding Reason dropdown trigger...')
        # Find the dropdown trigger for 'Reasoning'
        row = page.locator('h5:has-text("Reasoning")').locator('xpath=ancestor::div[contains(@class, "bg-white")]').first
        trigger = row.locator('div.cursor-pointer').first
        await trigger.click()
        
        print('Waiting for portal...')
        await page.wait_for_selector('div.fixed.w-\\[300px\\]', state='visible', timeout=5000)
        
        print('Taking screenshot of open dropdown...')
        await page.screenshot(path='dropdown_open.png')
        
        print('Scrolling the portal...')
        portal = page.locator('div.fixed.w-\\[300px\\]')
        await portal.evaluate('el => el.scrollBy(0, 50)')
        await page.wait_for_timeout(500)
        
        print('Clicking an option...')
        option = portal.locator('button').nth(1)
        option_text = await option.text_content()
        print('Selected option text:', option_text)
        await option.click()
        
        print('Waiting for dropdown to close...')
        await page.wait_for_selector('div.fixed.w-\\[300px\\]', state='hidden', timeout=5000)
        
        print('Taking final screenshot...')
        await page.screenshot(path='dropdown_closed.png')
        print('PASS')
        
        await browser.close()

asyncio.run(run())
