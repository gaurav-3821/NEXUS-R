import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto('http://127.0.0.1:5173/')
        await page.wait_for_selector('textarea', timeout=10000)
        await page.wait_for_timeout(2000)
        
        await page.fill('textarea', 'Hello')
        await page.press('textarea', 'Enter')
        
        await page.wait_for_timeout(3000)
        
        # Count the number of message bubbles
        bubbles = await page.locator('.msg-prose').count()
        print('Number of message bubbles:', bubbles)
        
        await page.screenshot(path='chat_separation.png')
        await browser.close()

asyncio.run(run())
