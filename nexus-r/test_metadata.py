import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Open Settings and turn on the toggle
        await page.goto('http://127.0.0.1:5173/settings/appearance')
        await page.wait_for_selector('text=Appearance Preview', timeout=10000)
        
        # Turn on the Show Response Metadata toggle
        # The easiest way is to evaluate in browser since we know it uses localStorage
        await page.evaluate("""
            const state = JSON.parse(localStorage.getItem('nexus-appearance') || '{}');
            state.showResponseMetadata = true;
            localStorage.setItem('nexus-appearance', JSON.stringify(state));
        """)
        
        # Navigate to chat
        await page.goto('http://127.0.0.1:5173/')
        await page.wait_for_selector('textarea', timeout=10000)
        
        # Wait for hydration
        await page.wait_for_timeout(2000)
        
        await page.fill('textarea', 'Hello')
        await page.press('textarea', 'Enter')
        
        await page.wait_for_timeout(5000)
        
        # Hover over the message to reveal the regenerate/metadata section
        # We need to hover over the assistant message's relative group
        assistant_messages = await page.locator('.group.text-gray-900').all()
        if assistant_messages:
            await assistant_messages[-1].hover()
            await page.wait_for_timeout(1000)
        
        # Take screenshot
        await page.screenshot(path='metadata_footer.png')
        await browser.close()

asyncio.run(run())
