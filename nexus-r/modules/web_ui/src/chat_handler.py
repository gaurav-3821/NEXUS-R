from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from nexus_r.events import Event, IntentResult, PermissionTier

logger = logging.getLogger("nexus-r.chat")


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
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._paused_browsers: dict[str, Any] = {}


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
        import re
        url_match = re.search(r'(?:go to|fetch|read|visit|open|browse)\s+(https?://[^\s]+)', message, re.IGNORECASE)
        search_match = re.search(r'(?:search the web for|search for|google|web search|look up)\s+(.+)', message, re.IGNORECASE)
        
        action_desc = ""
        extracted_text = ""
        
        if url_match:
            url = url_match.group(1)
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
                horizon_match = re.search(r'(?:next|horizon|predict|steps)\s+(\d+)', message, re.IGNORECASE)
                if horizon_match:
                    horizon = int(horizon_match.group(1))
                
                seq_match = re.search(r'(?:forecast|predict|timesfm)[^\[\(]*[\[\(]([\d\s\.,\-]+)[\]\)]', message, re.IGNORECASE)
                if not seq_match:
                    seq_match = re.search(r'(?:forecast|predict|timesfm)\s+(?:the\s+)?(?:next\s+\d+\s+)?(?:values|points|data|sequence)?\s*(?:for|of|sequence)?\s*([\d\s\.,\-]+)', message, re.IGNORECASE)
                
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

        if action_desc:
            if "TimesFM" in action_desc:
                message += f"\n\n[SYSTEM BACKGROUND ACTION: {action_desc}]\n[FORECAST CONTENT:]\n{extracted_text}\n[END FORECAST CONTENT]\nPlease present these forecasting results in a stunning, comprehensive report. Integrate an interactive tabbed UI artifact:\n- Tab 1: Forecast Visual (contains the box-drawing ASCII/Unicode visual chart within a code block, along with predictions table)\n- Tab 2: Statistical Analysis (includes average growth rates, historical volatility, and standard deviations)\n- Tab 3: Tactical Forecast Notes (interprets the trend direction and highlights any growth accelerations or anomalies)."
            else:
                message += f"\n\n[SYSTEM BACKGROUND ACTION: {action_desc}]\n[WEB CONTENT:]\n{extracted_text}\n[END WEB CONTENT]\nPlease answer the user's prompt using the web content above. Do not output the raw content, just summarize or answer based on it."

        msg_id = str(uuid4())
        ts = datetime.now(timezone.utc).isoformat()

        await self.event_store.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": message,
                "model": model or "",
                "timestamp": ts,
            },
        ))
        if self.ws_handler:
            await self.ws_handler.broadcast({
                "type": "chat_message_sent",
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "content": message,
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
        prefs = self.preference_engine.get_system_prompt_additions()
        
        # 3.5 Semantic Episodic Memory Injection
        context_block = await self.memory_engine.get_context_injection(message, conversation_id=conversation_id)
        
        # 4. Pattern Store Injection
        pattern = self.pattern_store.match(message)
        pattern_prompt = ""
        if pattern:
            pattern_prompt = self.pattern_store.get_prompt_injection(pattern)
            
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

When you output a `browser_action`, the system will execute it on the page, check for security walls (like CAPTCHA or MFA), take a screenshot, extract the updated visible page text, and feed it back to you. You can output ONE browser action per turn. Repeat this loop until your interactive workflow (login, trade, checkout, etc.) is fully completed.
"""
            
        final_prompt = message
        if prefs or pattern_prompt or context_block:
            final_prompt = f"{message}\n\n{prefs}\n{pattern_prompt}\n{context_block}"
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
        
        # 4.5 Eye of the Blind: Vision Fallback
        if intent.images and not self.router.registry.is_vision_model(preferred):
            vision_fallback = "qwen2.5-vl:7b"
            
            try:
                await self._ensure_ollama_model(vision_fallback)
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


    async def send_message(
        self,
        message: str,
        model: str | None = None,
        conversation_id: str | None = None,
        telemetry: dict[str, Any] | None = None,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        early_res, intent, routing, msg_id, ts, preferred, conversation_id = await self._prepare_intent(
            message=message, model=model, conversation_id=conversation_id, telemetry=telemetry, images=images
        )
        if early_res is not None:
            return early_res
            
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
            res = await self._finalize_response(
                response, conversation_id, msg_id, preferred,
                routing.selected_tier, started,
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
    ):
        import json
        
        async def stream_cb(val: str):
            yield val

        queue = asyncio.Queue()
        async def mock_cb(val: str):
            await queue.put(val)

        # We cannot easily yield from the callback, so we'll just let prepare_intent run
        # and if we needed to yield vision statuses, we'll collect them in a queue, but _prepare_intent is blocking.
        # So we skip real-time vision callback for now in stream_message or handle it differently.
        # For simplicity, we just pass None to stream_callback right now.
        
        early_res, intent, routing, msg_id, ts, preferred, conversation_id = await self._prepare_intent(
            message=message, model=model, conversation_id=conversation_id, telemetry=telemetry, images=images
        )

        if early_res is not None:
            # Yield early response as a stream
            yield f"data: {json.dumps({'type': 'status', 'value': 'routing'})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'value': early_res.get('content', '')})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'conversation_id': conversation_id, 'model': preferred})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'status', 'value': 'routing'})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'value': 'thinking'})}\n\n"
        
        started = datetime.now(timezone.utc)
        full_text = ""
        try:
            async for chunk in self.router.stream(intent, preferred):
                text = chunk.get("text", "")
                if text:
                    full_text += text
                    yield f"data: {json.dumps({'type': 'token', 'value': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"
            return
            
        yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'conversation_id': conversation_id, 'model': preferred})}\n\n"
        
        await self._log_response({
            "content": full_text,
            "model": preferred,
            "cost": routing.cost_estimate,
            "latency_ms": (datetime.now(timezone.utc) - started).total_seconds() * 1000,
            "blocked": False,
        }, conversation_id, msg_id, ts)

        tier_val = getattr(routing.selected_tier, "value", routing.selected_tier)
        if "byok" in routing.selected_model or "cloud" in routing.selected_model or (isinstance(tier_val, int) and tier_val >= 3):
            self.pattern_store.extract_and_save(message, full_text)
            
        asyncio.create_task(self.memory_engine.extract_memories(message, full_text, conversation_id=conversation_id))
            
        if telemetry:
            for k, v in telemetry.items():
                self.behavior_tracker.record_signal(k, v)
    async def _ensure_ollama_model(self, model_name: str) -> None:
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
                        
                # 3. Fail fast
                raise RuntimeError(f"Vision fallback model '{model_name}' is not installed. Please download it via the Download Center before attaching images.")
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

        step_limit = 6
        step_count = 0
        has_browser_action = True
        
        full_assistant_response = []

        try:
            while has_browser_action and step_count < step_limit:
                step_count += 1
                has_browser_action = False
                chunks.clear()
                
                mem = psutil.virtual_memory()
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
                            mem = psutil.virtual_memory()
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
                action_match = re.search(r'```browser_action\s*(.*?)\s*```', full_text, re.DOTALL)
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
                        else:
                            action_result = {"success": False, "error": f"Unknown action: {action}"}
                            
                        # Check for MFA / CAPTCHA intervention wall!
                        await self._check_and_handle_hitl(msg_id, conversation_id)
                        
                        # Capture updated visible text content and URL
                        updated_text = await self.browser.extract_text(max_chars=4000)
                        url = self.browser._page.url if self.browser._page else ""
                        
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

        response_data = {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "content": full_text,
            "role": "assistant",
            "model": model_name,
            "cost": cost,
            "latency_ms": round(elapsed, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._log_response(response_data, conversation_id, msg_id,
                                 response_data["timestamp"])
                                 
        # Memory Extraction
        asyncio.create_task(self.memory_engine.extract_memories(intent.raw_input, full_text, conversation_id=conversation_id))
        
        return response_data

    async def _finalize_response(self, response: dict, conversation_id: str,
                                 msg_id: str, model_name: str, tier,
                                 started: datetime) -> dict[str, Any]:
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
            },
        ))
        await self.cost_tracker.record(
            task_id=msg_id,
            amount=float(response_data.get("cost", 0)),
            model=str(response_data.get("model", "")),
            tier=PermissionTier.T2,
        )
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
            })

    async def get_conversations(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        events = await self.event_store.get_by_type("conversation_created")
        sorted_events = sorted(events, key=lambda e: e.data.get("created_at", ""), reverse=True)
        results = []
        for event in sorted_events[offset:offset + limit]:
            conv_id = event.data.get("conversation_id", "")
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
