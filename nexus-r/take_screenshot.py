from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto("http://localhost:8000")
        
        # Wait for the page to load
        page.wait_for_load_state("networkidle")
        
        # Force show the modal
        page.evaluate('document.getElementById("settingsModal").style.display = "flex";')
        
        # Force click the API keys tab just to initialize it if needed, or general tab
        page.evaluate('document.querySelector(".settings-tab-btn[data-target=\'settings-general\']").click();')
        
        time.sleep(1) # Extra wait for animation
        
        out_dir = r"C:\Users\Gaurav\.gemini\antigravity\brain\9b9c16c5-d005-4d33-82e9-a4e384f30159"
        
        page.screenshot(path=os.path.join(out_dir, "settings_general_new.png"))
        
        # Click API Keys tab
        page.evaluate('document.querySelector(".settings-tab-btn[data-target=\'settings-api-keys\']").click();')
        time.sleep(0.5)
        
        page.screenshot(path=os.path.join(out_dir, "settings_api_keys_new.png"))
        
        browser.close()

if __name__ == "__main__":
    run()
