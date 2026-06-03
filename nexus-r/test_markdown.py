import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on('console', lambda msg: print('CONSOLE:', msg.text))
        
        print('Navigating...')
        await page.goto('http://127.0.0.1:5173/')
        
        print('Waiting for chat input...')
        # The chat input might be a textarea with a specific placeholder
        await page.wait_for_selector('textarea', timeout=10000)
        
        # We need to make sure the chat app is fully hydrated
        await page.wait_for_timeout(2000)
        
        print('Typing into chat...')
        await page.fill('textarea', '**Hello**')
        
        print('Sending message...')
        # Click the send button, usually an svg or a button next to the textarea
        # Or just press Enter if that submits
        await page.press('textarea', 'Enter')
        
        print('Waiting for rendering...')
        await page.wait_for_timeout(2000)
        
        print('Taking after screenshot...')
        await page.screenshot(path='markdown_after.png')
        
        print('PASS')
        await browser.close()

asyncio.run(run())
