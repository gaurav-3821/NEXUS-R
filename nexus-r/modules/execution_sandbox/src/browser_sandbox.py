import asyncio
import logging
import os
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class AgenticBrowser:
    """
    Headless browser automation for NEXUS-R.
    Allows the agent to navigate to URLs, extract readable text,
    click elements, fill forms, and evaluate JavaScript.

    All public methods are protected by an asyncio lock for async-safety
    and include automatic fatal-error recovery (context recreation + one retry).
    """

    FATAL_ERROR_SUBSTRINGS = (
        "Target closed",
        "Browser disconnected",
        "Protocol error",
        "TimeoutError",
        "has been closed",
        "page crashed",
        "browser context has been closed",
    )

    def __init__(self, headless: bool = True, session_file: Optional[str] = None):
        self.headless = headless
        self._session_file = session_file
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()
        self.captured_api_data: list[dict] = []

    # ── Internal helpers ──────────────────────────────────

    def _is_fatal_error(self, e: Exception) -> bool:
        err_str = str(e)
        return any(fatal in err_str for fatal in self.FATAL_ERROR_SUBSTRINGS)

    async def _ensure_page(self):
        if self._page is None:
            await self._do_start()

    async def _recreate_context(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        self._context = None
        self._page = None

        if self._browser:
            try:
                if self._browser.is_connected():
                    self._context = await self._browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                    self._page = await self._context.new_page()
                    await self._apply_stealth_and_interception()
                    return
            except Exception:
                pass
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        # Full restart: reset playwright so _do_start rebuilds everything
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._playwright = None
        await self._do_start()

    async def _call_with_retry(self, fn, *args, error_return=None, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            if self._is_fatal_error(e):
                logger.warning("Fatal browser error: %s. Recreating context and retrying...", e)
                await self._recreate_context()
                await self._ensure_page()
                try:
                    return await fn(*args, **kwargs)
                except Exception as e2:
                    logger.error("Retry also failed: %s", e2)
                    return error_return
            raise

    # ── Lifecycle ─────────────────────────────────────────

    async def start(self):
        """Initializes the playwright browser session."""
        async with self._lock:
            await self._do_start()

    async def _do_start(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)

            # Auto-load session state if file exists
            storage_state = None
            if self._session_file and os.path.exists(self._session_file):
                try:
                    storage_state = await self.load_session_state(self._session_file)
                    logger.info("Loaded browser session state from %s", self._session_file)
                except Exception as exc:
                    logger.warning("Failed to load session state: %s", exc)

            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                storage_state=storage_state,
            )
            self._page = await self._context.new_page()
            await self._apply_stealth_and_interception()

    async def stop(self):
        """Closes the browser session and releases resources."""
        async with self._lock:
            await self._do_stop()

    async def _do_stop(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
            self._page = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # ── Session persistence ───────────────────────────────

    async def save_session_state(self, file_path: str) -> bool:
        """Save browser storage state (cookies, localStorage) to a JSON file."""
        if not self._context:
            return False
        try:
            state = await self._context.storage_state()
            import json
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self._session_file = file_path
            logger.info("Saved browser session state to %s", file_path)
            return True
        except Exception as e:
            logger.error("Failed to save session state: %s", e)
            return False

    async def load_session_state(self, file_path: str) -> Optional[dict]:
        """Load browser storage state from a JSON file."""
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._session_file = file_path
            return state
        except Exception as e:
            logger.error("Failed to load session state: %s", e)
            return None

    # ── Stealth / Anti-Bot ──────────────────────────────

    STEALTH_SCRIPT = """
    // Hide webdriver flag
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // Restore normal plugin count
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    // Set realistic language set
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    // Null out chrome automation objects
    window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {}, app: {} };
    // Override permissions query to avoid automated detection
    const _origQuery = navigator.permissions.query;
    navigator.permissions.query = (p) => p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : _origQuery(p);
    """

    async def _apply_stealth_and_interception(self):
        """Apply anti-bot stealth script and set up network data capture."""
        if not self._context or not self._page:
            return
        try:
            await self._context.add_init_script(self.STEALTH_SCRIPT)
        except Exception as e:
            logger.warning("Failed to apply stealth init script: %s", e)

        # Network interception — capture JSON API responses
        async def _on_response(response):
            try:
                res_type = response.request.resource_type
                if res_type not in ("xhr", "fetch"):
                    return
                ctype = response.headers.get("content-type", "")
                if "json" not in ctype:
                    return
                body = await response.json()
                entry = {
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "data": body,
                }
                self.captured_api_data.append(entry)
                if len(self.captured_api_data) > 50:
                    self.captured_api_data.pop(0)
            except Exception:
                pass

        self._page.on("response", lambda resp: asyncio.ensure_future(_on_response(resp)))

    def read_network_data(self, max_entries: int = 20) -> list[dict]:
        """Return captured API responses from the current browsing session."""
        return self.captured_api_data[-max_entries:]

    # ── Navigation ────────────────────────────────────────

    async def goto(self, url: str, timeout: int = 20000) -> Dict[str, Any]:
        """Navigate to a URL. Uses domcontentloaded to avoid infinite waits on SPAs."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_goto, url, timeout,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_goto(self, url: str, timeout: int = 20000) -> Dict[str, Any]:
        await self._ensure_page()
        try:
            if not url.startswith("http") and not url.startswith("file://"):
                url = "https://" + url

            response = await self._page.goto(
                url, wait_until="domcontentloaded", timeout=timeout
            )
            try:
                await self._page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            return {
                "success": True,
                "url": self._page.url,
                "status": response.status if response else None,
            }
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            logger.error(f"Browser goto error: {e}")
            return {"success": False, "error": str(e)}

    # ── Page interaction ──────────────────────────────────

    async def extract_text(self, max_chars: int = 8000) -> str:
        """Extract clean, readable text from the current page.

        Strips scripts/styles/iframes and returns plain text,
        capped at max_chars to conserve LLM token budget.
        """
        async with self._lock:
            return await self._call_with_retry(
                self._do_extract_text, max_chars,
                error_return="",
            )

    async def _do_extract_text(self, max_chars: int = 8000) -> str:
        await self._ensure_page()
        try:
            text = await self._page.evaluate('''() => {
                const junk = document.body.querySelectorAll(
                    'script, style, noscript, iframe, svg, nav, footer, header'
                );
                junk.forEach(el => el.remove());
                return document.body.innerText || document.body.textContent || "";
            }''')
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)[:max_chars]
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            logger.error(f"Browser extract_text error: {e}")
            return f"[Error extracting text: {e}]"

    async def screenshot(self) -> Optional[bytes]:
        """Take a screenshot of the current page. Returns PNG bytes."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_screenshot,
                error_return=None,
            )

    async def _do_screenshot(self) -> Optional[bytes]:
        await self._ensure_page()
        try:
            return await self._page.screenshot(full_page=False)
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            logger.error(f"Browser screenshot error: {e}")
            return None

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element by CSS selector."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_click, selector,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_click(self, selector: str) -> Dict[str, Any]:
        await self._ensure_page()
        try:
            await self._page.click(selector, timeout=5000)
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            return {"success": True}
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            return {"success": False, "error": str(e)}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an input element."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_type_text, selector, text,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_type_text(self, selector: str, text: str) -> Dict[str, Any]:
        await self._ensure_page()
        try:
            await self._page.fill(selector, text, timeout=5000)
            return {"success": True}
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            return {"success": False, "error": str(e)}

    async def evaluate(self, command: str) -> Dict[str, Any]:
        """Evaluate arbitrary JavaScript in the page context."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_evaluate, command,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_evaluate(self, command: str) -> Dict[str, Any]:
        await self._ensure_page()
        try:
            result = await self._page.evaluate(command)
            return {"success": True, "result": result}
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            return {"success": False, "error": str(e)}

    async def get_links(self) -> list:
        """Extract all links from the current page."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_get_links,
                error_return=[],
            )

    async def _do_get_links(self) -> list:
        await self._ensure_page()
        try:
            links = await self._page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim().substring(0, 100),
                    href: a.href
                })).filter(l => l.text && l.href.startsWith('http'));
            }''')
            return links[:50]
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            return []

    async def wait_for_element(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        """Wait for a CSS selector to become visible on the page."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_wait_for_element, selector, timeout,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_wait_for_element(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        await self._ensure_page()
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return {"success": True}
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            return {"success": False, "error": str(e)}

    # ── Compound searches ─────────────────────────────────

    async def search_web(self, query: str) -> Dict[str, Any]:
        """Perform a web search and return extracted results.

        Uses Brave Search (most headless-browser friendly) with
        fallback to raw text extraction.
        """
        async with self._lock:
            return await self._call_with_retry(
                self._do_search_web, query,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_search_web(self, query: str) -> Dict[str, Any]:
        import urllib.parse
        await self._ensure_page()

        url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
        nav = await self._do_goto(url, timeout=20000)
        if not nav.get("success"):
            return {"success": False, "error": nav.get("error", "Navigation failed")}

        try:
            results = await self._page.evaluate('''() => {
                const items = document.querySelectorAll('#results .snippet');
                if (items.length === 0) {
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

            text = await self._do_extract_text(max_chars=4000)
            return {"success": True, "results": [], "raw_text": text, "query": query}

        except Exception as e:
            if self._is_fatal_error(e):
                raise
            text = await self._do_extract_text(max_chars=4000)
            return {"success": True, "results": [], "raw_text": text, "query": query}

    async def search_images(self, query: str, max_images: int = 6) -> dict:
        """Search Google Images and return thumbnail URLs."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_search_images, query, max_images,
                error_return={"success": False, "error": "Fatal browser error", "images": []},
            )

    async def _do_search_images(self, query: str, max_images: int = 6) -> dict:
        await self._ensure_page()
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
            if self._is_fatal_error(e):
                raise
            return {'success': False, 'error': str(e), 'images': []}

    # ── Security / HITL ───────────────────────────────────

    async def detect_interception_wall(self) -> Optional[Dict[str, Any]]:
        """Scans the active page DOM for known CAPTCHA or MFA/OTP selectors."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_detect_interception_wall,
                error_return=None,
            )

    async def _do_detect_interception_wall(self) -> Optional[Dict[str, Any]]:
        await self._ensure_page()
        try:
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
                except Exception as inner_e:
                    if self._is_fatal_error(inner_e):
                        raise
                    continue

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
                except Exception as inner_e:
                    if self._is_fatal_error(inner_e):
                        raise
                    continue

            return None
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            logger.error(f"Error detecting interception wall: {e}")
            return None

    async def switch_to_headed(self) -> bool:
        """Saves current session state, closes headless browser, and restarts in headed mode at the same URL."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_switch_to_headed,
                error_return=False,
            )

    async def _do_switch_to_headed(self) -> bool:
        if not self._page or not self.headless:
            return False

        try:
            current_url = self._page.url
            state = await self._context.storage_state()

            await self._do_stop()

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

            await self._do_goto(current_url)
            return True
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            logger.error(f"Failed to switch to headed mode: {e}")
            return False

    async def fill_otp_code(self, selector: str, code: str) -> Dict[str, Any]:
        """Type OTP code received from the user into the detected input field."""
        async with self._lock:
            return await self._call_with_retry(
                self._do_fill_otp_code, selector, code,
                error_return={"success": False, "error": "Fatal browser error"},
            )

    async def _do_fill_otp_code(self, selector: str, code: str) -> Dict[str, Any]:
        await self._ensure_page()
        try:
            await self._page.fill(selector, code, timeout=5000)
            return {"success": True}
        except Exception as e:
            if self._is_fatal_error(e):
                raise
            return {"success": False, "error": f"Failed to fill OTP code: {e}"}
