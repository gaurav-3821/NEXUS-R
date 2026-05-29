import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class AgenticBrowser:
    """
    Headless browser automation for NEXUS-R.
    Allows the agent to navigate to URLs, extract readable text,
    click elements, fill forms, and evaluate JavaScript.
    """
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Initializes the playwright browser session."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self._page = await self._context.new_page()

    async def stop(self):
        """Closes the browser session and releases resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def goto(self, url: str, timeout: int = 20000) -> Dict[str, Any]:
        """Navigate to a URL. Uses domcontentloaded to avoid infinite waits on SPAs."""
        if not self._page:
            await self.start()
        
        try:
            if not url.startswith("http") and not url.startswith("file://"):
                url = "https://" + url
                
            response = await self._page.goto(
                url, wait_until="domcontentloaded", timeout=timeout
            )
            # Give the page a moment to render dynamic content
            try:
                await self._page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # If networkidle times out, domcontentloaded is good enough
                
            return {
                "success": True, 
                "url": self._page.url,
                "status": response.status if response else None,
            }
        except Exception as e:
            logger.error(f"Browser goto error: {e}")
            return {"success": False, "error": str(e)}

    async def extract_text(self, max_chars: int = 8000) -> str:
        """Extract clean, readable text from the current page.
        
        Strips scripts/styles/iframes and returns plain text,
        capped at max_chars to conserve LLM token budget.
        """
        if not self._page:
            return ""
            
        try:
            text = await self._page.evaluate('''() => {
                const junk = document.body.querySelectorAll(
                    'script, style, noscript, iframe, svg, nav, footer, header'
                );
                junk.forEach(el => el.remove());
                return document.body.innerText || document.body.textContent || "";
            }''')
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)[:max_chars]
        except Exception as e:
            logger.error(f"Browser extract_text error: {e}")
            return f"[Error extracting text: {e}]"

    async def screenshot(self) -> Optional[bytes]:
        """Take a screenshot of the current page. Returns PNG bytes."""
        if not self._page:
            return None
        try:
            return await self._page.screenshot(full_page=False)
        except Exception as e:
            logger.error(f"Browser screenshot error: {e}")
            return None

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element by CSS selector."""
        if not self._page:
            return {"success": False, "error": "Browser not started"}
            
        try:
            await self._page.click(selector, timeout=5000)
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an input element."""
        if not self._page:
            return {"success": False, "error": "Browser not started"}
            
        try:
            await self._page.fill(selector, text, timeout=5000)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def evaluate(self, command: str) -> Dict[str, Any]:
        """Evaluate arbitrary JavaScript in the page context."""
        if not self._page:
            return {"success": False, "error": "Browser not started"}
        try:
            result = await self._page.evaluate(command)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_links(self) -> list:
        """Extract all links from the current page."""
        if not self._page:
            return []
        try:
            links = await self._page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim().substring(0, 100),
                    href: a.href
                })).filter(l => l.text && l.href.startsWith('http'));
            }''')
            return links[:50]  # Cap at 50 links
        except Exception:
            return []

    async def search_web(self, query: str) -> Dict[str, Any]:
        """Perform a web search and return extracted results.
        
        Uses Brave Search (most headless-browser friendly) with
        fallback to raw text extraction.
        """
        import urllib.parse
        
        # Brave Search is the most headless-friendly search engine
        url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
        nav = await self.goto(url, timeout=20000)
        if not nav.get("success"):
            return {"success": False, "error": nav.get("error", "Navigation failed")}
        
        try:
            # Try to extract structured results from Brave
            results = await self._page.evaluate('''() => {
                // Brave Search result selectors
                const items = document.querySelectorAll('#results .snippet');
                if (items.length === 0) {
                    // Fallback: try generic link extraction
                    const links = document.querySelectorAll('a[href]');
                    return Array.from(links).filter(a => {
                        const href = a.href;
                        return href.startsWith('http') && 
                               !href.includes('brave.com') && 
                               a.innerText.trim().length > 10;
                    }).slice(0, 10).map(a => {
                        const container = a.closest('div') || a.parentElement;
                        const img = container ? container.querySelector('img[src]') : null;
                        const thumbSrc = img ? (img.getAttribute('src') || '') : '';
                        return {
                            title: a.innerText.trim().substring(0, 200),
                            url: a.href,
                            snippet: '',
                            thumbnail: (thumbSrc && !thumbSrc.startsWith('data:')) ? thumbSrc : ''
                        };
                    });
                }
                return Array.from(items).slice(0, 10).map(el => {
                    const titleEl = el.querySelector('.search-snippet-title, .title, .snippet-title, a');
                    const snippetEl = el.querySelector('.content, .snippet-description, .snippet-content');
                    const linkEl = el.querySelector('a[href]');
                    const imgEl = el.querySelector('img[src]');
                    const thumbSrc = imgEl ? (imgEl.getAttribute('src') || '') : '';
                    return {
                        title: titleEl ? titleEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href : '',
                        snippet: snippetEl ? snippetEl.innerText.trim() : '',
                        thumbnail: (thumbSrc && !thumbSrc.startsWith('data:')) ? thumbSrc : ''
                    };
                }).filter(r => r.title);
            }''')
            
            if results and len(results) > 0:
                return {"success": True, "results": results, "query": query}
            
            # Fallback: extract raw page text
            text = await self.extract_text(max_chars=4000)
            return {"success": True, "results": [], "raw_text": text, "query": query}
            
        except Exception as e:
            text = await self.extract_text(max_chars=4000)
            return {"success": True, "results": [], "raw_text": text, "query": query}

    async def search_images(self, query: str, max_images: int = 6) -> dict:
        """Search Google Images and return thumbnail URLs."""
        if not self._page:
            start_res = await self.start()
            if not start_res.get('success'):
                return {'success': False, 'error': 'Browser not started', 'images': []}
        try:
            import urllib.parse
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded}&tbm=isch"
            await self._page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await self._page.wait_for_timeout(2000)

            images = await self._page.evaluate(f'''
                () => {{
                    const results = [];
                    const imgs = document.querySelectorAll('img[data-src], img[src]');
                    for (const img of imgs) {{
                        if (results.length >= {max_images}) break;
                        const src = img.getAttribute('data-src') || img.getAttribute('src') || '';
                        if (!src || src.startsWith('data:') || src.includes('gstatic.com/images') || src.length < 20) continue;
                        const alt = img.getAttribute('alt') || '';
                        const link = img.closest('a');
                        const page_url = link ? link.getAttribute('href') || '' : '';
                        results.push({{ src, alt, page_url }});
                    }}
                    return results;
                }}
            ''')
            return {'success': True, 'images': images}
        except Exception as e:
            return {'success': False, 'error': str(e), 'images': []}

    async def detect_interception_wall(self) -> Optional[Dict[str, Any]]:
        """Scans the active page DOM for known CAPTCHA or MFA/OTP selectors."""
        if not self._page:
            return None
        try:
            # 1. Check for CAPTCHAs (iframe or class/id matching common patterns)
            captcha_selectors = [
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']",
                "iframe[src*='turnstile']",
                "iframe[src*='arkose']",
                ".g-recaptcha",
                "#challenge-form",
                "[class*='captcha']",
                "[id*='captcha']",
                "[src*='captcha']"
            ]
            for selector in captcha_selectors:
                try:
                    elements = await self._page.query_selector_all(selector)
                    for el in elements:
                        if await el.is_visible():
                            return {"type": "CAPTCHA", "selector": selector}
                except Exception:
                    continue

            # 2. Check for MFA / OTP / Verification Code fields
            mfa_patterns = [
                "input[name*='otp']",
                "input[name*='mfa']",
                "input[name*='code']",
                "input[name*='verification']",
                "input[name*='security']",
                "input[name*='token']",
                "input[id*='otp']",
                "input[id*='mfa']",
                "input[id*='code']",
                "input[id*='verification']",
                "input[id*='security']",
                "input[placeholder*='code' i]",
                "input[placeholder*='verification' i]",
                "input[placeholder*='OTP' i]",
                "input[type='tel'][maxlength='6']",
                "input[type='text'][maxlength='6']"
            ]
            for selector in mfa_patterns:
                try:
                    elements = await self._page.query_selector_all(selector)
                    for el in elements:
                        if await el.is_visible():
                            name = await el.get_attribute("name") or await el.get_attribute("id") or selector
                            return {"type": "MFA", "selector": selector, "name": name}
                except Exception:
                    continue
                        
            return None
        except Exception as e:
            logger.error(f"Error detecting interception wall: {e}")
            return None

    async def switch_to_headed(self) -> bool:
        """Saves current session state, closes headless browser, and restarts in headed mode at the same URL."""
        if not self._page or not self.headless:
            return False
        
        try:
            current_url = self._page.url
            # Save storage state (cookies, localStorage)
            state = await self._context.storage_state()
            
            # Stop current session
            await self.stop()
            
            # Re-launch with headless=False
            self.headless = False
            
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=False)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                storage_state=state
            )
            self._page = await self._context.new_page()
            
            # Navigate back to same URL
            await self.goto(current_url)
            return True
        except Exception as e:
            logger.error(f"Failed to switch to headed mode: {e}")
            return False

    async def fill_otp_code(self, selector: str, code: str) -> Dict[str, Any]:
        """Type OTP code received from the user into the detected input field."""
        if not self._page:
            return {"success": False, "error": "Browser not started"}
        try:
            await self._page.fill(selector, code, timeout=5000)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to fill OTP code: {e}"}


