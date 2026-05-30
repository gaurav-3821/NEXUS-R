from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto("http://localhost:8002")
        
        # Wait for the page to load
        page.wait_for_load_state("networkidle")
        time.sleep(1) # Extra wait for rendering
        
        out_dir = r"C:\Users\Gaurav\.gemini\antigravity\brain\9b9c16c5-d005-4d33-82e9-a4e384f30159"
        
        page.screenshot(path=os.path.join(out_dir, "new_chat_ui.png"))
        
        browser.close()

if __name__ == "__main__":
    run()
