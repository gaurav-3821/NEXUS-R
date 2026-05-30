from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto("http://localhost:8002")
        
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # Click settings button to see if JS is alive
        try:
            page.click("#openSettingsBtn", timeout=2000)
            time.sleep(1)
            
            out_dir = r"C:\Users\Gaurav\.gemini\antigravity\brain\9b9c16c5-d005-4d33-82e9-a4e384f30159"
            page.screenshot(path=os.path.join(out_dir, "test_settings_open.png"))
            print("Successfully clicked settings and took screenshot!")
        except Exception as e:
            print("Failed to click settings:", e)
        
        browser.close()

if __name__ == "__main__":
    run()
