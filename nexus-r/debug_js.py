from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Capture console logs and errors
        page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))
        
        page.goto("http://localhost:8002")
        page.wait_for_load_state("networkidle")
        browser.close()

if __name__ == "__main__":
    run()
