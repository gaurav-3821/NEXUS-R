from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from nexus_r.events import Event, IntentResult, PermissionTier
from modules.cognition_router.src.research_engine import PipelineContext
from modules.cognition_router.src.query_router import QueryRouter
from modules.cognition_router.src.golden_memory import GoldenMemory
from modules.cognition_router.src.planner_critic import PlannerSkill, CriticSkill

logger = logging.getLogger("nexus-r.chat")


# --- Psutil cache to avoid per-token syscalls ---
_psutil_cache: dict[str, object] = {"mem": None, "ts": 0.0}

def _cached_virtual_memory():
    """Return psutil.virtual_memory(), cached for 10 seconds."""
    import time as _time
    now = _time.time()
    if _psutil_cache["mem"] is None or now - _psutil_cache["ts"] > 10.0:
        import psutil
        _psutil_cache["mem"] = psutil.virtual_memory()
        _psutil_cache["ts"] = now
    return _psutil_cache["mem"]


def _is_trivial_message(msg: str) -> bool:
    """Check if a message is trivial (greeting, short ack, etc.)."""
    words = msg.split()
    if len(words) > 8:
        return False
    trivial = {
        'hi', 'hello', 'hey', 'thanks', 'thank', 'ok', 'okay', 'bye',
        'yes', 'no', 'sure', 'cool', 'nice', 'great', 'awesome', 'wow',
        'lol', 'haha', 'good', 'morning', 'night', 'please', 'help',
    }
    stripped = msg.lower().strip().rstrip('!?.')
    return stripped in trivial or (len(words) <= 3 and all(w.lower().rstrip('!?.') in trivial for w in words))


def _needs_artifact_prompt(msg: str) -> bool:
    """Check if the message likely needs artifact/browser system instructions."""
    lower = msg.lower()
    keywords = [
        'chart', 'graph', 'plot', 'diagram', 'visual', 'tabs', 'table',
        'artifact', 'html', 'interactive', 'demo', 'ui', 'mockup',
        'browse', 'search the web', 'go to', 'navigate', 'fetch',
        'visit', 'open http', 'forecast', 'predict', 'timesfm',
    ]
    return any(kw in lower for kw in keywords)

# Pre-compiled Regex patterns for Intent Parsing
import re
URL_PATTERN = re.compile(r'(?:go to|fetch|read|visit|open|browse)\s+(https?://[^\s]+)', re.IGNORECASE)
SEARCH_PATTERN = re.compile(r'(?:search the web for|search for|google|web search|look up)\s+(.+)', re.IGNORECASE)
HORIZON_PATTERN = re.compile(r'(?:next|horizon|predict|steps)\s+(\d+)', re.IGNORECASE)
SEQ_BRACKET_PATTERN = re.compile(r'(?:forecast|predict|timesfm)[^\[\(]*[\[\(]([\d\s\.,\-]+)[\]\)]', re.IGNORECASE)
SEQ_NATURAL_PATTERN = re.compile(r'(?:forecast|predict|timesfm)\s+(?:the\s+)?(?:next\s+\d+\s+)?(?:values|points|data|sequence)?\s*(?:for|of|sequence)?\s*([\d\s\.,\-]+)', re.IGNORECASE)
BROWSER_ACTION_PATTERN = re.compile(r'```browser_action\s*(.*?)\s*```', re.DOTALL)

class ChatHandler:
    def __init__(
        self,
        event_store,
        cost_tracker,
        router,
        ws_handler=None,
        perms=None,
    ) -> None:
        self.event_store = event_store
        self.cost_tracker = cost_tracker
        self.router = router
        self.ws_handler = ws_handler
        self.perms = perms
        
        # Phase 3 Personalization Modules
        from modules.input_gateway.src.memory_parser import MemoryParser
        from modules.web_ui.src.preference_engine import PreferenceEngine
        from modules.web_ui.src.pattern_store import PatternStore
        from modules.state_core.src.behavior_tracker import BehaviorTracker
        from modules.execution_sandbox.src.calculator import SafeCalculator
        from modules.execution_sandbox.src.browser_sandbox import AgenticBrowser
        from modules.state_core.src.identity_store import IdentityStore
        from modules.state_core.src.memory_engine import SemanticMemoryEngine
        
        # Initialize IdentityStore (in reality, might be passed from app.py)
        import os
        workspace = os.environ.get("NEXUS_WORKSPACE_ROOT", os.getcwd())
        self.identity_store = IdentityStore(f"{workspace}/.nexus-r/identity")
        self.memory_engine = SemanticMemoryEngine(f"{workspace}/.nexus-r/events.db")
        
        self.memory_parser = MemoryParser()
        self.preference_engine = PreferenceEngine(self.identity_store)
        self.pattern_store = PatternStore(workspace)
        self.behavior_tracker = BehaviorTracker(self.identity_store)
        self.calculator = SafeCalculator()
        self.browser = AgenticBrowser()
        
        # Initialize Search Registry & Research Engine
        from modules.cognition_router.src.providers.search.__init__ import SearchProviderRegistry
        from modules.cognition_router.src.providers.search.searxng_provider import SearxngProvider
        from modules.cognition_router.src.providers.search.playwright_provider import PlaywrightProvider
        from modules.cognition_router.src.research_engine import ResearchEngine
        
        self.search_registry = SearchProviderRegistry()
        self.search_registry.register(SearxngProvider(), role="search")
        playwright_provider = PlaywrightProvider(self.browser)
        self.search_registry.register(playwright_provider, role="search")
        self.search_registry.register(playwright_provider, role="extract")
        
        self.research_engine = ResearchEngine(self.search_registry)

        # ── Widget Registry ──────────────────────────────────────
        from modules.cognition_router.src.providers.widget_registry import WidgetRegistry
        from modules.cognition_router.src.providers.widgets.weather_widget import WeatherWidget
        from modules.cognition_router.src.providers.widgets.calculator_widget import CalculatorWidget
        from modules.cognition_router.src.providers.widgets.stock_widget import StockWidget
        from modules.cognition_router.src.providers.widgets.citation_widget import CitationWidget
        from modules.cognition_router.src.providers.widgets.router_decision_widget import RouterDecisionWidget
        from modules.cognition_router.src.providers.widgets.model_status_widget import ModelStatusWidget
        from modules.cognition_router.src.providers.widgets.memory_widget import MemoryWidget
        from modules.cognition_router.src.providers.widgets.cost_analytics_widget import CostAnalyticsWidget
        self.widget_registry = WidgetRegistry()
        self.widget_registry.register(WeatherWidget())
        self.widget_registry.register(CalculatorWidget(self.calculator))
        self.widget_registry.register(StockWidget())
        self.widget_registry.register(CitationWidget())
        self.widget_registry.register(RouterDecisionWidget())
        self.widget_registry.register(ModelStatusWidget())
        self.widget_registry.register(MemoryWidget())
        self.widget_registry.register(CostAnalyticsWidget())

        # ── Hybrid Architecture: QueryRouter, GoldenMemory, Planner-Critic ──
        workspace = os.environ.get("NEXUS_WORKSPACE_ROOT", os.getcwd())
        self.query_router = QueryRouter()
        self.golden_memory = GoldenMemory(f"{workspace}/.nexus-r/events.db")
        self.planner = PlannerSkill()
        self.critic = CriticSkill()

        self._active_tasks: dict[str, asyncio.Task] = {}
        self._paused_browsers: dict[str, Any] = {}
        self._persistent_memory_enabled = True
        self._smart_memory_enabled = True


    async def _prepare_intent(
        self,
        message: str,
        model: str | None = None,
        conversation_id: str | None = None,
        telemetry: dict[str, Any] | None = None,
        images: list[str] | None = None,
        stream_callback=None,
    ) -> tuple[dict | None, IntentResult | None, Any | None, str, str, str, str]:
        if model in ("Auto Router", "System Default"):
            model = None
            
        if not conversation_id:
            conversation_id = "conv_" + str(uuid4())
            await self.event_store.append(Event(
                event_type="conversation_created",
                data={
                    "conversation_id": conversation_id,
                    "title": message[:80],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "message_count": 0,
                },
            ))
            if self.ws_handler:
                await self.ws_handler.broadcast({
                    "type": "conversation_created",
                    "conversation_id": conversation_id,
                    "title": message[:80],
                })

        # 1. Check Calculator Bypass
        calc_result = self.calculator.evaluate(message)
        if calc_result is not None:
            msg_id = str(uuid4())
            ts = datetime.now(timezone.utc).isoformat()
            await self._log_response({
                "content": calc_result,
                "model": "calculator",
                "cost": 0.0,
                "latency_ms": 1.0,
                "blocked": False,
            }, conversation_id, msg_id, ts)
            return {
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": calc_result,
                "role": "assistant",
                "model": "calculator",
                "cost": 0.0,
                "latency_ms": 1.0,
                "timestamp": ts,
            }, None, None, msg_id, ts, "calculator", conversation_id

        # 1.5 Check Trivial Bypass
        if _is_trivial_message(message):
            import random
            stripped = message.lower().strip().rstrip('!?.')
            if stripped in ('hi', 'hello', 'hey', 'morning', 'night'):
                resp = random.choice(["Hello! How can I help you?", "Hi there!", "Greetings!"])
            elif stripped in ('thanks', 'thank', 'thank you'):
                resp = random.choice(["You're welcome!", "Anytime!", "Glad I could help."])
            elif stripped in ('bye', 'goodbye'):
                resp = random.choice(["Goodbye!", "Have a great day!", "See you later!"])
            elif stripped in ('ok', 'okay', 'sure', 'yes', 'no', 'cool', 'nice', 'great', 'awesome', 'wow'):
                resp = "Got it."
            else:
                resp = "Acknowledged."
                
            msg_id = str(uuid4())
            ts = datetime.now(timezone.utc).isoformat()
            await self._log_response({
                "content": resp,
                "model": "system_trivial_bypass",
                "cost": 0.0,
                "latency_ms": 1.0,
                "blocked": False,
            }, conversation_id, msg_id, ts)
            return {
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": resp,
                "role": "assistant",
                "model": "system_trivial",
                "cost": 0.0,
                "latency_ms": 1.0,
                "timestamp": ts,
            }, None, None, msg_id, ts, "system_trivial", conversation_id

        # 2. Check Memory Commands
        memory_intent = self.memory_parser.parse(message)
        if memory_intent:
            action = memory_intent["action"]
            content = memory_intent["content"]
            response_text = ""
            if action == "remember":
                self.preference_engine.add_explicit_preference(content)
                response_text = f"Got it. I will remember: {content}"
            elif action == "forget":
                success = self.preference_engine.remove_explicit_preference(content)
                response_text = f"Forgotten." if success else "I couldn't find that memory."
            elif action == "list":
                response_text = self.preference_engine.get_all_preferences_formatted()
                
            msg_id = str(uuid4())
            ts = datetime.now(timezone.utc).isoformat()
            await self._log_response({
                "content": response_text,
                "model": "memory_parser",
                "cost": 0.0,
                "latency_ms": 1.0,
                "blocked": False,
            }, conversation_id, msg_id, ts)
            return {
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": response_text,
                "role": "assistant",
                "model": "memory_parser",
                "cost": 0.0,
                "latency_ms": 1.0,
                "timestamp": ts,
            }, None, None, msg_id, ts, "memory_parser", conversation_id

        # 2.5 Check Browser Intents
        url_match = URL_PATTERN.search(message)
        search_match = SEARCH_PATTERN.search(message)
        
        action_desc = ""
        extracted_text = ""
        
        if url_match:
            url = url_match.group(1)
            if self.ws_handler:
                await self.ws_handler.broadcast({
                    "type": "chat_message_sent",
                    "message_id": "sys_" + str(uuid4()),
                    "conversation_id": conversation_id,
                    "content": f"Navigating to {url}...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "processing",
                    "streaming": True,
                })
            res = await self.browser.goto(url)
            if res.get("success"):
                extracted_text = await self.browser.extract_text()
                action_desc = f"Navigated to {url}"
            else:
                action_desc = f"Failed to navigate to {url}: {res.get('error')}"
                
        elif search_match:
            query = search_match.group(1).strip()
            if (query.startswith('"') and query.endswith('"')) or (query.startswith("'") and query.endswith("'")):
                query = query[1:-1].strip()
            elif query.endswith('"') or query.endswith("'"):
                query = query[:-1].strip()
            elif query.startswith('"') or query.startswith("'"):
                query = query[1:].strip()
            if self.ws_handler:
                await self.ws_handler.broadcast({
                    "type": "chat_message_sent",
                    "message_id": "sys_" + str(uuid4()),
                    "conversation_id": conversation_id,
                    "content": f"Searching the web for '{query}'...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "processing",
                    "streaming": True,
                })
                
            search_res = await self.browser.search_web(query)
            image_res = await self.browser.search_images(query) if hasattr(self.browser, "search_images") else {}
            
            if search_res.get("success"):
                results = search_res.get("results", [])
                images = image_res.get("images", []) if image_res.get("success") else []
                
                self._pending_search_broadcast = {
                    "results": results,
                    "images": images,
                    "query": query
                }
                
                if results:
                    formatted_items = []
                    for r in results:
                        title_clean = " ".join([line.strip() for line in r['title'].split('\n') if line.strip()])
                        formatted_items.append(f"- **{title_clean}** ({r['url']}): {r['snippet']}")
                    formatted = "\n".join(formatted_items)
                    extracted_text = f"Search results for '{query}':\n{formatted}"
                else:
                    extracted_text = search_res.get("raw_text", "No results found.")
                action_desc = f"Searched the web for '{query}'"
            else:
                action_desc = f"Failed to search for '{query}': {search_res.get('error')}"
        
        # 2.6 Check Forecasting Intents
        is_forecast_query = any(keyword in message.lower() for keyword in ["forecast", "predict", "timesfm"])
        
        if not action_desc and is_forecast_query:
            try:
                horizon = 5
                horizon_match = HORIZON_PATTERN.search(message)
                if horizon_match:
                    horizon = int(horizon_match.group(1))
                
                seq_match = SEQ_BRACKET_PATTERN.search(message)
                if not seq_match:
                    seq_match = SEQ_NATURAL_PATTERN.search(message)
                
                if seq_match:
                    numbers_str = seq_match.group(1)
                    raw_nums = re.split(r'[\s,]+', numbers_str.strip())
                    history_data = []
                    for val in raw_nums:
                        if val.strip():
                            clean_val = val.replace('[', '').replace(']', '').replace('(', '').replace(')', '').strip()
                            if clean_val:
                                history_data.append(float(clean_val))
                                
                    if len(history_data) >= 3:
                        from modules.execution_sandbox.src.forecaster import TimesFMForecaster
                        forecaster = TimesFMForecaster()
                        fc_res = forecaster.forecast(history_data, horizon=horizon)
                        if fc_res.get("success"):
                            fc_data = fc_res.get("forecast", [])
                            fc_lower = fc_res.get("lower_bound", [])
                            fc_upper = fc_res.get("upper_bound", [])
                            fc_metrics = fc_res.get("metrics", {})
                            
                            formatted_fc = "\n".join([
                                f"- Step {i+1}: **{fc_data[i]}** (Quantiles: {fc_lower[i]} to {fc_upper[i]})"
                                for i in range(len(fc_data))
                            ])
                            
                            metrics_summary = "\n".join([
                                f"- {k.replace('_', ' ').title()}: **{v}**"
                                for k, v in fc_metrics.items()
                            ])
                            
                            extracted_text = (
                                f"TimesFM Zero-Shot Forecast Results (Horizon: {horizon}):\n"
                                f"Historical Sequence: {history_data}\n\n"
                                f"Predictions:\n{formatted_fc}\n\n"
                                f"Statistical Characteristics:\n{metrics_summary}\n\n"
                                f"Visual Forecast Plot:\n```\n{fc_res['ascii_chart']}\n```"
                            )
                            action_desc = f"Generated TimesFM zero-shot forecast for sequence of length {len(history_data)}"
            except Exception as e:
                logger.error(f"Error parsing forecasting intent: {e}")

        # Save the clean user message BEFORE appending system context
        # This is what the frontend will display in the user's chat bubble
        user_display_message = message

        if action_desc:
            if "TimesFM" in action_desc:
                message += f"\n\n[SYSTEM BACKGROUND ACTION: {action_desc}]\n[FORECAST CONTENT:]\n{extracted_text}\n[END FORECAST CONTENT]\nPlease present these forecasting results. You MUST use the following exact JSON format inside a ```artifact code block to render a tabbed UI:\n```artifact\n{{\n  \"title\": \"TimesFM Forecast\",\n  \"type\": \"analysis\",\n  \"tabs\": [\n    {{ \"label\": \"Visual\", \"content\": \"markdown here\" }},\n    {{ \"label\": \"Stats\", \"content\": \"markdown here\" }}\n  ]\n}}\n```"
            else:
                message += f"\n\n[SYSTEM BACKGROUND ACTION: {action_desc}]\n[WEB CONTENT:]\n{extracted_text}\n[END WEB CONTENT]\nPlease answer the user's prompt using the web content above. If you want to show a stunning interactive HTML visualization (like a styled card or chart), you MUST put your full HTML code inside a ```html_artifact code block. Otherwise, just summarize normally."


        msg_id = str(uuid4())
        ts = datetime.now(timezone.utc).isoformat()

        # Fire-and-forget: don't block the response pipeline on event logging
        # Store the CLEAN user message, not the LLM-enriched prompt
        asyncio.create_task(self.event_store.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": user_display_message,
                "model": model or "",
                "timestamp": ts,
            },
        )))
        if self.ws_handler:
            # Broadcast the CLEAN user message to the frontend UI
            await self.ws_handler.broadcast({
                "type": "chat_message_sent",
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": user_display_message,
                "timestamp": ts,
            })
            
            if getattr(self, "_pending_search_broadcast", None):
                await self.ws_handler.broadcast({
                    "type": "search_results",
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "results": self._pending_search_broadcast["results"],
                    "images": self._pending_search_broadcast["images"],
                    "query": self._pending_search_broadcast["query"],
                })
                self._pending_search_broadcast = None

        if self.perms:
            from nexus_r.events import Action
            decision = await self.perms.check(
                Action(name="general_llm", tier=PermissionTier.T2, target="chat"),
                PermissionTier.T2,
            )
            if not decision.allowed:
                result = {
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "content": "Message blocked by trust layer.",
                    "role": "assistant",
                    "model": "",
                    "cost": 0.0,
                    "latency_ms": 0,
                    "timestamp": ts,
                    "blocked": True,
                }
                await self._log_response(result, conversation_id, msg_id, ts)
                return result, None, None, msg_id, ts, "", conversation_id

        # 3. Preference Engine Injection
        # 3.5 Semantic Episodic Memory Injection
        # 4. Pattern Store Injection
        # Parallelize I/O reads
        def _get_pattern_sync():
            p = self.pattern_store.match(message)
            return self.pattern_store.get_prompt_injection(p) if p else ""
            
        async def _get_mem_async():
            if not _is_trivial_message(message):
                return await self.memory_engine.get_context_injection(message, conversation_id=conversation_id)
            return ""

        prefs, context_block, pattern_prompt = await asyncio.gather(
            asyncio.to_thread(self.preference_engine.get_system_prompt_additions),
            _get_mem_async(),
            asyncio.to_thread(_get_pattern_sync)
        )
            
        artifact_instruction = """
[SYSTEM INSTRUCTION]
You have the ability to render interactive UI components. 

1. **Tabbed Interface**: Output a JSON block inside a Markdown code block with language `artifact`:
```artifact
{
  "type": "tabs",
  "title": "Optional Title",
  "tabs": [
    { "label": "Tab 1", "content": "Markdown content for tab 1" },
    { "label": "Tab 2", "content": "Markdown content for tab 2" }
  ]
}
```

2. **Interactive HTML/JS Visualizations**: To build an interactive demo, visual explanation, UI mockup, or diagram, output self-contained HTML/CSS/JS inside an `html_artifact` block:
```html_artifact
<!DOCTYPE html>
<html>
<head>
  <style> body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f0f4f8; } .box { padding: 20px; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s; } .box:hover { transform: scale(1.05); } </style>
</head>
<body>
  <div class="box" onclick="alert('Clicked!')">Interactive Demo</div>
  <script> console.log("Ready"); </script>
</body>
</html>
```

3. **Charts**: Output Chart.js JSON inside a `chart` block for data visualization.

Always prefer visual output (HTML artifacts or charts) for questions about concepts, comparisons, data, or processes!
"""

        browser_agent_instruction = """
[BROWSER TOOL AGENT INSTRUCTION]
You are equipped with a live Agentic Headless Browser. You can execute multiple interactive steps to fill forms, log in, register, navigate to carts, or execute mock share trading.
To run a browser action, output a structured JSON block inside a Markdown code block with language "browser_action":
```browser_action
{
  "action": "click",
  "selector": "#submit-btn"
}
```
Or to fill an input field:
```browser_action
{
  "action": "type",
  "selector": "input[type='email']",
  "text": "user@example.com"
}
```
Or to go to a new URL:
```browser_action
{
  "action": "goto",
  "url": "https://example.com/checkout"
}
```
Or to wait for a specific element to be visible:
```browser_action
{
  "action": "wait",
  "selector": ".payment-success"
}
```
Or to execute arbitrary JavaScript on the page (the result is returned to you):
```browser_action
{
  "action": "evaluate",
  "code": "document.querySelector('.price').innerText"
}
```
Or to read captured API/JSON data from network requests made during the page visit:
```browser_action
{
  "action": "read_network_data",
  "max_entries": 10
}
```
```

When you output a `browser_action`, the system will execute it on the page, check for security walls (like CAPTCHA or MFA), take a screenshot, extract the updated visible page text, and feed it back to you. You can output ONE browser action per turn. Repeat this loop until your interactive workflow (login, trade, checkout, etc.) is fully completed.
"""
            
        final_prompt = message
        if prefs or pattern_prompt or context_block:
            final_prompt = f"{message}\n\n{prefs}\n{pattern_prompt}\n{context_block}"
        # Only inject heavy system instructions when the message likely needs them
        if _needs_artifact_prompt(message):
            final_prompt += f"\n\n{artifact_instruction}\n\n{browser_agent_instruction}"

        intent = IntentResult(
            raw_input=message,
            normalized_input=final_prompt,
            task_type="general_llm",
            images=images,
            complexity=0.5,
            confidence=0.8,
            parameters={"prompt": message},
            suggested_tier=PermissionTier.T2,
        )
        try:
            routing = await self.router.route(intent)
            preferred = model or routing.selected_model
        except RuntimeError as e:
            if "exhausted" in str(e).lower() or "probe failed" in str(e).lower():
                from fastapi import HTTPException
                raise HTTPException(status_code=503, detail="No AI models are currently available. Please start Ollama or configure an API key in the settings.")
            raise

        def _tier_index(tier) -> int:
            if tier is None:
                return -1
            if isinstance(tier, int):
                return tier
            val = getattr(tier, "value", tier) if not isinstance(tier, (int, str)) else tier
            if isinstance(val, int):
                return val
            s = str(val).lower().replace("t", "")
            try:
                return int(s)
            except (ValueError, TypeError):
                return -1

        # ── Phase 1: QueryRouter — override tier based on complexity assessment ──
        if model is None or model in ("Auto Router", "System Default"):
            try:
                has_local = hasattr(self.router, 'models') and self.router.models.local.is_available
                has_cloud = hasattr(self.router, 'models') and self.router.models.byok.is_available
                qr_result = await self.query_router.evaluate(intent.raw_input)
                tier_val = _tier_index(routing.selected_tier if hasattr(routing, "selected_tier") else None)
                if qr_result.route == "cloud" and has_cloud and tier_val < 3:
                    logger.info("QueryRouter escalated to cloud: %s", qr_result.reason)
                    routing.selected_tier = PermissionTier.T3
                    routing.selected_model = "byok"
                    routing.cost_estimate = 0.05
                    preferred = "byok"
                elif qr_result.route == "cloud" and not has_cloud:
                    logger.info("QueryRouter wants cloud but no provider; staying local: %s", qr_result.reason)
                elif qr_result.route == "local" and has_local and tier_val >= 3:
                    logger.info("QueryRouter de-escalated to local: %s", qr_result.reason)
                    routing.selected_tier = PermissionTier.T1
                    routing.selected_model = "local"
                    routing.cost_estimate = 0.001
                    preferred = "local"
            except Exception as qr_err:
                logger.debug("QueryRouter evaluation skipped: %s", qr_err)

        # ── Phase 2: GoldenMemory — inject few-shot examples from cloud history ──
        tier_val = _tier_index(routing.selected_tier if hasattr(routing, "selected_tier") else None)
        if tier_val < 3:
            try:
                few_shot = await self.golden_memory.format_few_shot(intent.raw_input, max_examples=2)
                if few_shot:
                    intent.normalized_input = f"{few_shot}\n\n{intent.normalized_input}"
                    logger.debug("Injected %d golden examples into local model context", 2)
            except Exception as gm_err:
                logger.debug("GoldenMemory retrieval skipped: %s", gm_err)

        self._last_user_query = message

        # 4.5 Eye of the Blind: Vision Fallback
        if intent.images and not self.router.registry.is_vision_model(preferred):
            vision_fallback = "qwen2.5-vl:7b"
            
            try:
                await self._ensure_ollama_model(vision_fallback, msg_id, conversation_id)
            except RuntimeError as e:
                err_msg = str(e)
                msg_id = str(uuid4())
                ts = datetime.now(timezone.utc).isoformat()
                return {
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "content": err_msg,
                    "role": "assistant",
                    "model": "system",
                    "cost": 0.0,
                    "latency_ms": 1.0,
                    "timestamp": ts,
                    "blocked": True,
                }, None, None, msg_id, ts, "system", conversation_id
            
            from litellm import acompletion
            vision_prompt = "Please describe this image in detail, specifically focusing on information that would help answer the following user query: " + intent.raw_input
            
            msg_content = [{"type": "text", "text": vision_prompt}]
            for img in intent.images:
                msg_content.append({"type": "image_url", "image_url": {"url": img}})
                
            try:
                if self.ws_handler:
                    await self.ws_handler.broadcast({
                        "type": "chat_message_sent",
                        "message_id": "sys_vision_" + str(uuid4()),
                        "conversation_id": conversation_id,
                        "content": "Running Eye of the Blind vision fallback...",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "processing",
                        "streaming": True,
                    })
                if stream_callback:
                    import json
                    await stream_callback(f"data: {json.dumps({'type': 'status', 'value': 'analyzing image'})}\n\n")
                    
                vision_res = await acompletion(
                    model="ollama/" + vision_fallback,
                    messages=[{"role": "user", "content": msg_content}],
                    api_base="http://127.0.0.1:11434"
                )
                vision_desc = vision_res.choices[0].message.content
                
                desc_block = f"\n\n[SYSTEM BACKGROUND ACTION: Image visually analyzed by {vision_fallback}]\n[IMAGE DESCRIPTION]\n{vision_desc}\n[END IMAGE DESCRIPTION]\n"
                intent.normalized_input += desc_block
                intent.images = None
                
            except Exception as e:
                logger.error(f"Vision fallback failed: {e}")
                intent.normalized_input += "\n\n[SYSTEM BACKGROUND ACTION: Vision fallback failed to describe the image.]"
                intent.images = None

        return None, intent, routing, msg_id, ts, preferred, conversation_id

    async def _run_widgets(self, raw_input: str, research_result=None, router_decision=None):
        """Build PipelineContext and run all registered widgets."""
        memory_facts = []
        try:
            if not _is_trivial_message(raw_input):
                facts = await self.memory_engine.recall(raw_input, top_k=10)
                if facts:
                    memory_facts = facts
        except Exception:
            pass
        from modules.cognition_router.src.research_engine import PipelineContext
        ctx = PipelineContext(
            raw_input=raw_input,
            research_result=research_result,
            memory_facts=memory_facts,
            router_decision=router_decision or {},
        )
        results = await self.widget_registry.execute_all(ctx)
        return [{"type": r.widget_type, "data": r.data, "title": r.title} for r in results]

    async def send_message(
        self,
        message: str,
        model: str | None = None,
        conversation_id: str | None = None,
        telemetry: dict[str, Any] | None = None,
        images: list[str] | None = None,
        mode: str = "balanced",
        search_enabled: bool = False,
        search_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        early_res, intent, routing, msg_id, ts, preferred, conversation_id = await self._prepare_intent(
            message=message, model=model, conversation_id=conversation_id, telemetry=telemetry, images=images
        )
        if early_res is not None:
            return early_res

        final_prompt = intent.normalized_input
        if search_enabled and mode != "speed":
            research = await self.research_engine.run(intent, mode, search_sources or ["web"])
            
            if research.context_for_prompt:
                final_prompt = f"[Research Context]\n{research.context_for_prompt}\n\n{intent.normalized_input}"

        intent.normalized_input = final_prompt
            
        started = datetime.now(timezone.utc)
        if self.ws_handler:
            task = asyncio.create_task(self._stream_response(
                conversation_id=conversation_id,
                msg_id=msg_id,
                intent=intent,
                preferred=preferred,
                routing=routing,
                started=started,
            ))
            self._active_tasks[msg_id] = task
            return {
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "status": "processing",
                "model": preferred,
                "estimated_cost": routing.cost_estimate,
            }
        else:
            response = await self.router.complete(intent, preferred)
            try:
                route_name = routing.selected_tier.name if hasattr(routing.selected_tier, "name") else str(routing.selected_tier)
                non_ws_widgets = await self._run_widgets(
                    raw_input=message,
                    research_result=research if search_enabled and mode != "speed" else None,
                    router_decision={"model": preferred, "tier": route_name, "cost_estimate": routing.cost_estimate},
                )
            except Exception as wid_e:
                logger.warning("Widget execution failed in non-WS path: %s", wid_e)
                non_ws_widgets = []
            res = await self._finalize_response(
                response, conversation_id, msg_id, preferred,
                routing.selected_tier, started, widgets=non_ws_widgets,
            )
            
            tier_val = getattr(routing.selected_tier, "value", routing.selected_tier)
            if "byok" in routing.selected_model or "cloud" in routing.selected_model or (isinstance(tier_val, int) and tier_val >= 3):
                self.pattern_store.extract_and_save(message, res.get("content", ""))
                
            asyncio.create_task(self.memory_engine.extract_memories(message, res.get("content", ""), conversation_id=conversation_id))
                
            if telemetry:
                for k, v in telemetry.items():
                    self.behavior_tracker.record_signal(k, v)
                    
            return res

    async def stream_message(
        self,
        message: str,
        model: str | None = None,
        conversation_id: str | None = None,
        telemetry: dict[str, Any] | None = None,
        images: list[str] | None = None,
        mode: str = "balanced",
        search_enabled: bool = False,
        search_sources: list[str] | None = None,
    ):
        import json
        
        async def stream_cb(val: str):
            yield val

        queue = asyncio.Queue()
        async def mock_cb(val: str):
            await queue.put(val)

        early_res, intent, routing, msg_id, ts, preferred, conversation_id = await self._prepare_intent(
            message=message, model=model, conversation_id=conversation_id, telemetry=telemetry, images=images
        )

        if early_res is not None:
            yield f"data: {json.dumps({'type': 'status', 'value': 'routing'})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'value': early_res.get('content', '')})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'conversation_id': conversation_id, 'model': preferred})}\n\n"
            return

        final_prompt = intent.normalized_input

        if search_enabled and mode != "speed":
            research = await self.research_engine.run(intent, mode, search_sources or ["web"])

            if research.sources:
                sources_payload = [{'title': s[0], 'url': s[1], 'content': s[2]} for s in research.sources]
                yield f"data: {json.dumps({'type': 'sources', 'data': sources_payload}, default=str)}\n\n"

            if research.context_for_prompt:
                # Ensure the user's raw input stays at the bottom to prevent context dilution
                final_prompt = f"[Research Context]\n{research.context_for_prompt}\n\n{intent.normalized_input}"

        intent.normalized_input = final_prompt

        yield f"data: {json.dumps({'type': 'status', 'value': 'routing'})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'value': 'thinking'})}\n\n"
        
        started = datetime.now(timezone.utc)
        full_text = ""
        reasoning_tokens: int | None = None
        try:
            async for chunk in self.router.stream(intent, preferred):
                text = chunk.get("text", "")
                if text:
                    full_text += text
                    yield f"data: {json.dumps({'type': 'token', 'value': text})}\n\n"
                rt = chunk.get("reasoning_tokens")
                if rt is not None:
                    reasoning_tokens = rt
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"
            return
        latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        provider = preferred.split("/")[0] if "/" in preferred else "ollama"
        route_name = routing.selected_tier.name if hasattr(routing.selected_tier, "name") else str(routing.selected_tier)
        
        metadata = {
            "model": preferred,
            "provider": provider,
            "route": route_name,
            "latency_ms": latency,
            "cost": routing.cost_estimate,
        }
        if reasoning_tokens is not None:
            metadata["reasoning_tokens"] = reasoning_tokens

        try:
            widgets = await self._run_widgets(
                raw_input=message,
                research_result=research if search_enabled and mode != "speed" else None,
                router_decision={"model": preferred, "tier": route_name, "cost_estimate": routing.cost_estimate},
            )
            for w in widgets:
                yield f"data: {json.dumps({'type': 'widget', 'widget_type': w['type'], 'data': w['data'], 'title': w['title']})}\n\n"
        except Exception as wid_e:
            logger.warning("Widget execution failed in SSE path: %s", wid_e, exc_info=True)
            widgets = []
        
        yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'conversation_id': conversation_id, 'model': preferred, 'metadata': metadata})}\n\n"
        
        await self._log_response({
            "content": full_text,
            "model": preferred,
            "cost": routing.cost_estimate,
            "latency_ms": latency,
            "blocked": False,
            "widgets": widgets,
        }, conversation_id, msg_id, ts)

        tier_val = getattr(routing.selected_tier, "value", routing.selected_tier)
        if "byok" in routing.selected_model or "cloud" in routing.selected_model or (isinstance(tier_val, int) and tier_val >= 3):
            self.pattern_store.extract_and_save(message, full_text)
            
        asyncio.create_task(self.memory_engine.extract_memories(message, full_text, conversation_id=conversation_id))
            
        if telemetry:
            for k, v in telemetry.items():
                self.behavior_tracker.record_signal(k, v)
    async def _ensure_ollama_model(self, model_name: str, msg_id: str = "", conversation_id: str = "") -> None:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                # 1. Ping check
                try:
                    res = await client.get("http://127.0.0.1:11434/", timeout=0.5)
                except (httpx.ConnectError, httpx.TimeoutException):
                    raise RuntimeError("Ollama is not running or unavailable. Please start Ollama to use vision fallback.")
                
                # 2. Model verification
                res = await client.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
                if res.status_code == 200:
                    tags = [m["name"] for m in res.json().get("models", [])]
                    if any(model_name in t or t in model_name for t in tags):
                        return # Exists
                        
                # 3. Auto-pull
                if self.ws_handler and msg_id and conversation_id:
                    await self.ws_handler.broadcast({
                        "type": "chat_status",
                        "message_id": msg_id,
                        "conversation_id": conversation_id,
                        "state": "downloading",
                        "stage": f"Pulling vision model {model_name}...",
                        "reasoning_chunk": f"\n\n[SYSTEM] Downloading required vision model {model_name} from Ollama. This may take a few minutes...\n"
                    })
                
                process = await asyncio.create_subprocess_exec(
                    "ollama", "pull", model_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    raise RuntimeError(f"Failed to auto-pull vision model '{model_name}': {stderr.decode()}")
        except Exception as e:
            logger.error(f"Failed to ensure ollama model {model_name}: {e}")
            raise e

    async def interrupt_message(self, message_id: str) -> bool:
        task = self._active_tasks.get(message_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def resume_hitl(self, message_id: str, code: str | None = None, solved: bool = False) -> bool:
        """Resumes a paused browser session that was blocked by CAPTCHA/MFA."""
        if message_id not in self._paused_browsers:
            logger.warning(f"No paused browser session found for message_id {message_id}")
            return False
            
        session = self._paused_browsers[message_id]
        session["response"] = {"code": code, "solved": solved}
        session["event"].set()
        return True

    async def _check_and_handle_hitl(self, msg_id: str, conversation_id: str) -> None:
        """Checks if the browser has hit an MFA or CAPTCHA screen.
        If so, pauses execution, alerts the user, and waits for validation/resume.
        """
        wall = await self.browser.detect_interception_wall()
        if not wall:
            return

        logger.warning(f"Interception wall detected on browser: {wall}")
        
        # Take a screenshot
        screenshot_bytes = await self.browser.screenshot()
        import base64
        screenshot_b64 = ""
        if screenshot_bytes:
            screenshot_b64 = "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode("utf-8")
            
        # Notify the user via WebSocket
        if self.ws_handler:
            await self.ws_handler.broadcast({
                "type": "hitl_intervention_required",
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "wall_type": wall["type"],
                "selector": wall.get("selector"),
                "name": wall.get("name", "Challenge"),
                "screenshot": screenshot_b64,
                "prompt": (
                    f"Action Required: A {wall['type']} challenge was detected. "
                    "Please solve it in the headed browser window or input the OTP code below."
                )
            })

        # Switch to headed mode dynamically so the user can interact directly on local desktop
        await self.browser.switch_to_headed()
        
        # Create pause event
        event = asyncio.Event()
        self._paused_browsers[msg_id] = {
            "event": event,
            "response": None
        }
        
        try:
            # Yield control back to event loop until user resumes
            await event.wait()
            
            response = self._paused_browsers[msg_id]["response"]
            if response:
                if response.get("code") and wall.get("selector"):
                    # Type OTP code
                    await self.browser.fill_otp_code(wall["selector"], response["code"])
                    # Press enter or submit if needed
                    try:
                        await self.browser._page.keyboard.press("Enter")
                    except Exception:
                        pass
        finally:
            if msg_id in self._paused_browsers:
                del self._paused_browsers[msg_id]

    async def _stream_response(self, conversation_id: str, msg_id: str,
                                intent: IntentResult, preferred: str,
                                routing, started: datetime) -> dict[str, Any]:
        chunks: list[str] = []
        
        # Determine active tools based on the query
        active_tools = []
        if "search" in intent.raw_input.lower() or "google" in intent.raw_input.lower():
            active_tools.append("playwright_search")
        if "forecast" in intent.raw_input.lower() or "predict" in intent.raw_input.lower():
            active_tools.append("timesfm_forecaster")

        import psutil
        import re
        import json

        # ── Phase 3: Planner-Critic — generate and review plan for cloud/browser tasks ──
        tier_val = getattr(routing.selected_tier, "value", 0) if hasattr(routing, "selected_tier") else 0
        if tier_val >= 3 and active_tools:
            try:
                plan = await self.planner.plan(intent.raw_input, context=str(active_tools))
                if plan:
                    review = await self.critic.review(plan, intent.raw_input)
                    if not review.approved and review.revised_plan:
                        plan = review.revised_plan
                    plan_prompt = self.planner.format_for_prompt(plan)
                    intent.normalized_input = f"{plan_prompt}\n\n{intent.normalized_input}"
                    if self.ws_handler:
                        status = "approved" if review.approved else "revised"
                        await self.ws_handler.broadcast({
                            "type": "chat_status",
                            "message_id": msg_id,
                            "conversation_id": conversation_id,
                            "state": "planning",
                            "stage": f"Plan {status} ({plan.estimated_complexity}, {len(plan.steps)} steps)",
                        })
            except Exception as pc_err:
                logger.debug("Planner-Critic skipped: %s", pc_err)

        step_limit = 6
        step_count = 0
        has_browser_action = True
        max_time_seconds = 60
        loop_start_time = asyncio.get_running_loop().time()

        full_assistant_response = []

        try:
            while has_browser_action and step_count < step_limit:
                # Max time guardrail
                elapsed = asyncio.get_running_loop().time() - loop_start_time
                if elapsed > max_time_seconds:
                    logger.info("Browser action loop exceeded %ss, aborting", max_time_seconds)
                    if self.ws_handler:
                        await self.ws_handler.broadcast({
                            "type": "chat_chunk",
                            "message_id": msg_id,
                            "conversation_id": conversation_id,
                            "text": f"\n\n*⏱ Browser action time limit ({max_time_seconds}s) reached. Continuing with data gathered so far...*",
                            "model_name": preferred,
                            "done": False,
                        })
                    intent.normalized_input += f"\n\n[SYSTEM] Browser action loop exceeded {max_time_seconds}s time limit. Continuing with data gathered so far."
                    break

                step_count += 1
                has_browser_action = False
                chunks.clear()
                
                mem = _cached_virtual_memory()
                mem_usage = f"{mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB"

                # 1. Start generation state
                if self.ws_handler:
                    await self.ws_handler.broadcast({
                        "type": "chat_status",
                        "message_id": msg_id,
                        "conversation_id": conversation_id,
                        "state": "generating",
                        "stage": f"generating (turn {step_count})" if step_count > 1 else "generating",
                    })
                    
                    await self.ws_handler.broadcast({
                        "type": "chat_metrics",
                        "message_id": msg_id,
                        "conversation_id": conversation_id,
                        "renderer": "Artifacts / Tabbed UI / Charts" if active_tools else "Markdown / LaTeX",
                        "token_speed": "0 tok/s",
                        "execution_time": f"{(datetime.now(timezone.utc) - started).total_seconds():.1f}s",
                        "active_tools": active_tools,
                        "memory_usage": mem_usage,
                    })

                token_count = 0
                in_think_block = False
                async for chunk in self.router.stream(intent, preferred):
                    text = chunk.get("text", "")
                    token_count += 1
                    
                    if "<think>" in text:
                        in_think_block = True
                        text = text.replace("<think>", "")
                        if self.ws_handler:
                            await self.ws_handler.broadcast({
                                "type": "chat_status",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "state": "reasoning",
                                "stage": "thinking",
                            })

                    if "</think>" in text:
                        in_think_block = False
                        text = text.replace("</think>", "")
                        if self.ws_handler:
                            await self.ws_handler.broadcast({
                                "type": "chat_status",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "state": "generating",
                                "stage": "generating",
                            })

                    if in_think_block and text:
                        if self.ws_handler:
                            await self.ws_handler.broadcast({
                                "type": "chat_status",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "state": "reasoning",
                                "stage": "thinking",
                                "reasoning_chunk": text
                            })
                        continue

                    if text:
                        chunks.append(text)
                    
                    # Emit metrics live during generation
                    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                    speed = f"{token_count / elapsed:.1f} tok/s" if elapsed > 0 else "0 tok/s"
                    
                    if self.ws_handler and text:
                        await self.ws_handler.broadcast({
                            "type": "chat_chunk",
                            "message_id": msg_id,
                            "conversation_id": conversation_id,
                            "text": text,
                            "model_name": chunk.get("model_name", preferred),
                            "done": chunk.get("done", False),
                        })
                        
                        if token_count % 5 == 0:  # throttling metrics to avoid flooding ws
                            mem = _cached_virtual_memory()
                            mem_usage = f"{mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB"
                            
                            metrics_payload = {
                                "type": "chat_metrics",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "renderer": "Artifacts / Tabbed UI / Charts" if active_tools else "Markdown / LaTeX",
                                "speed": speed,
                                "execution_time": f"{elapsed:.1f}s",
                                "active_tools": active_tools or "None",
                                "memory_usage": mem_usage,
                            }
                            
                            if hasattr(self.router.registry, "_last_model_reason") and self.router.registry._last_model_reason:
                                metrics_payload["auto_model"] = preferred
                                metrics_payload["auto_model_reason"] = self.router.registry._last_model_reason
                                
                            await self.ws_handler.broadcast(metrics_payload)
                    if chunk.get("done"):
                        break

                full_text = "".join(chunks)
                full_assistant_response.append(full_text)
                
                # Check for browser action blocks
                action_match = BROWSER_ACTION_PATTERN.search(full_text)
                if action_match:
                    action_json_str = action_match.group(1).strip()
                    try:
                        action_data = json.loads(action_json_str)
                        action = action_data.get("action")
                        has_browser_action = True
                        
                        if "playwright_search" not in active_tools:
                            active_tools.append("playwright_search")
                        
                        if self.ws_handler:
                            await self.ws_handler.broadcast({
                                "type": "chat_status",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "state": "executing",
                                "stage": f"Browser Action: {action}",
                                "reasoning_chunk": f"\n\n[SYSTEM] Executing browser action: {action} on {action_data.get('selector', action_data.get('url', ''))}...\n"
                            })
                            
                        # Ensure browser is started
                        await self.browser.start()
                        
                        action_result = {}
                        if action == "goto":
                            action_result = await self.browser.goto(action_data.get("url"))
                        elif action == "click":
                            action_result = await self.browser.click(action_data.get("selector"))
                        elif action == "type":
                            action_result = await self.browser.type_text(action_data.get("selector"), action_data.get("text"))
                        elif action == "wait":
                            action_result = await self.browser.wait_for_element(action_data.get("selector"))
                        elif action == "evaluate":
                            action_result = await self.browser.evaluate(action_data.get("code", ""))
                        elif action == "read_network_data":
                            entries = action_data.get("max_entries", 20)
                            data = self.browser.read_network_data(max_entries=entries)
                            action_result = {"success": True, "data": data}
                        else:
                            action_result = {"success": False, "error": f"Unknown action: {action}"}
                            
                        # Check for MFA / CAPTCHA intervention wall!
                        await self._check_and_handle_hitl(msg_id, conversation_id)
                        
                        # Capture updated visible text content and URL
                        updated_text = await self.browser.extract_text(max_chars=4000)
                        url = self.browser._page.url if self.browser._page else ""

                        # Push scraped content into semantic memory
                        if updated_text and len(updated_text) > 50:
                            try:
                                await self.memory_engine.extract_memories(updated_text, "")
                            except Exception as mem_err:
                                logger.warning("Failed to extract memories from browser content: %s", mem_err)
                        
                        result_msg = (
                            f"\n\n[SYSTEM ACTION RESULT]\n"
                            f"Action: {action} (Success: {action_result.get('success', False)})\n"
                            f"Current URL: {url}\n"
                            f"[VISIBLE PAGE CONTENT:]\n{updated_text}\n[END VISIBLE PAGE CONTENT]\n"
                        )
                        
                        # Ingest the result directly back into intent normalized input for the next turn
                        intent.normalized_input += f"\n\nUser Action input: execute action {action_json_str}\n" + result_msg
                        
                        # Emit a tiny chunk to alert frontend of action result
                        if self.ws_handler:
                            await self.ws_handler.broadcast({
                                "type": "chat_chunk",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "text": f"\n\n*Action executed: {action}. Response received. Continuing...*",
                                "model_name": preferred,
                                "done": False,
                            })
                            
                    except Exception as e:
                        logger.error(f"Error executing browser action: {e}")
                        intent.normalized_input += f"\n\n[SYSTEM ERROR] Failed to execute browser action: {e}"
                        if self.ws_handler:
                            await self.ws_handler.broadcast({
                                "type": "chat_chunk",
                                "message_id": msg_id,
                                "conversation_id": conversation_id,
                                "text": f"\n\n*Failed to execute browser action: {e}. Continuing...*",
                                "model_name": preferred,
                                "done": False,
                            })

            # Emit final metrics
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            speed = f"{(token_count * step_count) / elapsed:.1f} tok/s" if elapsed > 0 else "0 tok/s"
            if self.ws_handler:
                import psutil
                mem = psutil.virtual_memory()
                mem_usage = f"{mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB"
                await self.ws_handler.broadcast({
                    "type": "chat_metrics",
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "renderer": "Artifacts / Tabbed UI / Charts" if active_tools else "Markdown / LaTeX",
                    "token_speed": speed,
                    "execution_time": f"{elapsed:.1f}s",
                    "active_tools": active_tools,
                    "memory_usage": mem_usage,
                })

        except asyncio.CancelledError:
            logger.info("Chat stream task %s cancelled by user request", msg_id)
            if self.ws_handler:
                await self.ws_handler.broadcast({
                    "type": "chat_status",
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "state": "failed",
                    "stage": "finalizing",
                    "reasoning_chunk": "\nInterrupted by user."
                })
                await self.ws_handler.broadcast({
                    "type": "chat_error",
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "error": "Interrupted by user.",
                })
            raise
        finally:
            if msg_id in self._active_tasks:
                del self._active_tasks[msg_id]

        full_text = "\n\n".join(full_assistant_response)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        cost = (routing.cost_estimate * step_count) if full_text else 0.0
        model_name = preferred

        route_name = routing.selected_tier.name if hasattr(routing.selected_tier, "name") else str(routing.selected_tier)
        try:
            widgets = await self._run_widgets(
                raw_input=intent.raw_input,
                router_decision={"model": preferred, "tier": route_name, "cost_estimate": routing.cost_estimate},
            )
        except Exception as wid_e:
            logger.warning("Widget execution failed in WS path: %s", wid_e)
            widgets = []

        response_data = {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "content": full_text,
            "role": "assistant",
            "model": model_name,
            "cost": cost,
            "latency_ms": round(elapsed, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "widgets": widgets,
        }
        await self._log_response(response_data, conversation_id, msg_id,
                                 response_data["timestamp"])
                                 
        # Memory Extraction
        asyncio.create_task(self.memory_engine.extract_memories(intent.raw_input, full_text, conversation_id=conversation_id))
        
        return response_data

    async def _finalize_response(self, response: dict, conversation_id: str,
                                 msg_id: str, model_name: str, tier,
                                 started: datetime, widgets: list | None = None) -> dict[str, Any]:
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        cost = float(response.get("cost", 0))
        full_text = response.get("text", "")
        response_data = {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "content": full_text,
            "role": "assistant",
            "model": response.get("model_name", model_name),
            "cost": cost,
            "latency_ms": round(elapsed, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "widgets": widgets or [],
        }
        await self._log_response(response_data, conversation_id, msg_id,
                                 response_data["timestamp"])
        return response_data

    async def _log_response(self, response_data: dict, conversation_id: str,
                             msg_id: str, ts: str) -> None:
        await self.event_store.append(Event(
            event_type="chat_message_received",
            data={
                "message_id": msg_id,
                "parent_message_id": msg_id,
                "conversation_id": conversation_id,
                "content": response_data.get("content", ""),
                "role": "assistant",
                "model": response_data.get("model", ""),
                "cost": response_data.get("cost", 0.0),
                "latency_ms": response_data.get("latency_ms", 0),
                "timestamp": ts,
                "blocked": response_data.get("blocked", False),
                "widgets": response_data.get("widgets", []),
            },
        ))
        await self.cost_tracker.record(
            task_id=msg_id,
            amount=float(response_data.get("cost", 0)),
            model=str(response_data.get("model", "")),
            tier=PermissionTier.T2,
        )

        # ── Phase 2: GoldenMemory store — capture cloud model successes ──
        model_name = str(response_data.get("model", ""))
        content = response_data.get("content", "")
        blocked = response_data.get("blocked", False)
        cost_val = float(response_data.get("cost", 0))
        is_cloud = cost_val > 0.01 or any(kw in model_name.lower() for kw in ("byok", "groq", "openai", "anthropic", "google/"))
        if not blocked and content and len(content) > 100 and (is_cloud or cost_val > 0.001):
            asyncio.create_task(self.golden_memory.store(
                query=getattr(self, "_last_user_query", ""),
                reasoning_steps=content[:2000],
                final_result=content[:500],
                task_type="general",
                model_used=model_name,
                success_score=min(1.0, cost_val * 10) if cost_val > 0 else 0.5,
                metadata={"latency_ms": response_data.get("latency_ms", 0)},
            ))

        if self.ws_handler:
            await self.ws_handler.notify_cost_update(
                task_id=msg_id,
                amount=float(response_data.get("cost", 0)),
                model=str(response_data.get("model", "")),
                tier="T2",
            )
            await self.ws_handler.broadcast({
                "type": "chat_done",
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": response_data.get("content", ""),
                "cost": response_data.get("cost", 0),
                "latency_ms": response_data.get("latency_ms", 0),
                "model": response_data.get("model", ""),
                "timestamp": ts,
                "widgets": response_data.get("widgets", []),
            })

    async def delete_conversation(self, conversation_id: str) -> bool:
        event = Event(
            event_type="conversation_deleted",
            data={
                "conversation_id": conversation_id,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self.event_store.append(event)
        return True

    async def clear_all_conversations(self) -> bool:
        convs = await self.get_conversations(limit=1000)
        for c in convs:
            await self.delete_conversation(c["conversation_id"])
        return True

    async def get_conversations(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        events = await self.event_store.get_by_type("conversation_created")
        deleted_events = await self.event_store.get_by_type("conversation_deleted")
        deleted_ids = {e.data.get("conversation_id") for e in deleted_events if e.data.get("conversation_id")}
        sorted_events = sorted(events, key=lambda e: e.data.get("created_at", ""), reverse=True)
        results = []
        for event in sorted_events:
            if len(results) >= limit:
                break
            conv_id = event.data.get("conversation_id", "")
            if conv_id in deleted_ids:
                continue
            if offset > 0:
                offset -= 1
                continue
            count = await self._get_message_count(conv_id)
            results.append({
                "conversation_id": conv_id,
                "title": event.data.get("title", ""),
                "created_at": event.data.get("created_at", ""),
                "message_count": count,
            })
        return results

    async def get_history(
        self,
        conversation_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        sent = await self.event_store.get_by_type("chat_message_sent")
        received = await self.event_store.get_by_type("chat_message_received")
        all_msgs: list[dict[str, Any]] = []
        for event in sent:
            if conversation_id and event.data.get("conversation_id") != conversation_id:
                continue
            all_msgs.append({
                "message_id": event.data.get("message_id", ""),
                "conversation_id": event.data.get("conversation_id", ""),
                "content": event.data.get("content", ""),
                "role": "user",
                "model": event.data.get("model", ""),
                "cost": 0.0,
                "timestamp": event.data.get("timestamp", ""),
            })
        for event in received:
            if conversation_id and event.data.get("conversation_id") != conversation_id:
                continue
            all_msgs.append({
                "message_id": event.data.get("message_id", ""),
                "conversation_id": event.data.get("conversation_id", ""),
                "content": event.data.get("content", ""),
                "role": "assistant",
                "model": event.data.get("model", ""),
                "cost": float(event.data.get("cost", 0)),
                "latency_ms": float(event.data.get("latency_ms", 0)),
                "timestamp": event.data.get("timestamp", ""),
                "blocked": bool(event.data.get("blocked", False)),
                "widgets": event.data.get("widgets", []),
            })
        all_msgs.sort(key=lambda m: m.get("timestamp", ""))
        return all_msgs[offset:offset + limit]

    async def get_message(self, message_id: str) -> dict[str, Any] | None:
        for event_type in ("chat_message_sent", "chat_message_received"):
            events = await self.event_store.get_by_type(event_type)
            for event in events:
                if event.data.get("message_id") == message_id:
                    return {
                        "message_id": event.data.get("message_id", ""),
                        "conversation_id": event.data.get("conversation_id", ""),
                        "content": event.data.get("content", ""),
                        "role": "assistant" if event_type == "chat_message_received" else "user",
                        "model": event.data.get("model", ""),
                        "cost": float(event.data.get("cost", 0)),
                        "timestamp": event.data.get("timestamp", ""),
                    }
        return None

    async def _get_message_count(self, conversation_id: str) -> int:
        sent = await self.event_store.get_by_type("chat_message_sent")
        return sum(1 for e in sent if e.data.get("conversation_id") == conversation_id)

    # --- Projects ---

    async def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        project_id = "proj_" + str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        event = Event(
            event_type="project_created",
            data={"project_id": project_id, "name": name, "description": description, "created_at": now},
        )
        await self.event_store.append(event)
        return {"project_id": project_id, "name": name, "description": description, "created_at": now, "conversation_ids": []}

    async def get_projects(self) -> list[dict[str, Any]]:
        created = await self.event_store.get_by_type("project_created")
        deleted = await self.event_store.get_by_type("project_deleted")
        updated = await self.event_store.get_by_type("project_updated")
        added = await self.event_store.get_by_type("project_conversation_added")
        removed = await self.event_store.get_by_type("project_conversation_removed")

        deleted_ids = {e.data["project_id"] for e in deleted if e.data.get("project_id")}

        # Build project-conversation map
        conv_map: dict[str, set[str]] = {}
        for e in added:
            pid = e.data.get("project_id")
            cid = e.data.get("conversation_id")
            if pid and cid:
                conv_map.setdefault(pid, set()).add(cid)
        for e in removed:
            pid = e.data.get("project_id")
            cid = e.data.get("conversation_id")
            if pid and cid and pid in conv_map:
                conv_map[pid].discard(cid)

        # Latest name/description from update events
        name_map: dict[str, str] = {}
        desc_map: dict[str, str] = {}
        for e in updated:
            pid = e.data.get("project_id")
            if pid and pid not in deleted_ids:
                if e.data.get("name"):
                    name_map[pid] = e.data["name"]
                if "description" in e.data:
                    desc_map[pid] = e.data["description"]

        results = []
        for e in created:
            pid = e.data.get("project_id", "")
            if pid in deleted_ids:
                continue
            results.append({
                "project_id": pid,
                "name": name_map.get(pid, e.data.get("name", "")),
                "description": desc_map.get(pid, e.data.get("description", "")),
                "created_at": e.data.get("created_at", ""),
                "conversation_ids": list(conv_map.get(pid, set())),
            })
        return results

    async def update_project(self, project_id: str, name: str | None = None, description: str | None = None) -> bool:
        event = Event(
            event_type="project_updated",
            data={"project_id": project_id, "name": name, "description": description},
        )
        await self.event_store.append(event)
        return True

    async def delete_project(self, project_id: str) -> bool:
        event = Event(
            event_type="project_deleted",
            data={"project_id": project_id, "deleted_at": datetime.now(timezone.utc).isoformat()},
        )
        await self.event_store.append(event)
        return True

    async def add_conversation_to_project(self, project_id: str, conversation_id: str) -> bool:
        event = Event(
            event_type="project_conversation_added",
            data={"project_id": project_id, "conversation_id": conversation_id},
        )
        await self.event_store.append(event)
        return True

    async def remove_conversation_from_project(self, project_id: str, conversation_id: str) -> bool:
        event = Event(
            event_type="project_conversation_removed",
            data={"project_id": project_id, "conversation_id": conversation_id},
        )
        await self.event_store.append(event)
        return True
