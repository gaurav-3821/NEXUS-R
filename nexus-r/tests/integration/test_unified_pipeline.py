import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from modules.web_ui.src.chat_handler import ChatHandler
from nexus_r.events import IntentResult, PermissionTier

@pytest.fixture
def mock_router():
    router = MagicMock()
    
    class MockDecision:
        def __init__(self):
            self.selected_model = "test_model"
            self.cost_estimate = 0.0
            self.selected_tier = PermissionTier.T2
            self.is_cache_hit = False

    async def mock_route(intent):
        return MockDecision()

    async def mock_complete(intent, preferred):
        return {
            "text": "Router Response",
            "model": preferred,
            "cost": 0.0,
            "latency_ms": 100,
            "blocked": False,
        }

    async def mock_stream(intent, preferred):
        yield {"text": "Router "}
        yield {"text": "Response"}

    router.route = AsyncMock(side_effect=mock_route)
    router.complete = AsyncMock(side_effect=mock_complete)
    router.stream = mock_stream
    router.registry = MagicMock()
    router.registry.is_vision_model = MagicMock(return_value=False)
    return router

@pytest.fixture
def mock_deps():
    return {
        "event_store": AsyncMock(),
        "cost_tracker": AsyncMock(),
        "ws_handler": None,
        "perms": AsyncMock(),
    }

@pytest.fixture
def chat_handler(mock_router, mock_deps):
    with patch("modules.state_core.src.identity_store.IdentityStore"), \
         patch("modules.state_core.src.memory_engine.SemanticMemoryEngine"), \
         patch("modules.web_ui.src.preference_engine.PreferenceEngine"), \
         patch("modules.web_ui.src.pattern_store.PatternStore"), \
         patch("modules.state_core.src.behavior_tracker.BehaviorTracker"):
        
        handler = ChatHandler(
            event_store=mock_deps["event_store"],
            cost_tracker=mock_deps["cost_tracker"],
            router=mock_router,
            ws_handler=mock_deps["ws_handler"],
            perms=mock_deps["perms"]
        )
        
        # Setup perms mock
        class MockPermDecision:
            def __init__(self, allowed=True):
                self.allowed = allowed
        handler.perms.check = AsyncMock(return_value=MockPermDecision(True))
        
        # Setup memory engine mock
        handler.memory_engine.get_context_injection = AsyncMock(return_value="")
        handler.memory_engine.extract_memories = AsyncMock()
        
        return handler

async def gather_stream(stream_gen):
    events = []
    async for item in stream_gen:
        if item.startswith("data: "):
            try:
                events.append(json.loads(item[6:].strip()))
            except json.JSONDecodeError:
                pass
    return events

@pytest.mark.asyncio
async def test_calculator_parity(chat_handler):
    message = "What is 25 * 4?"
    chat_handler.calculator.evaluate = MagicMock(return_value="100")
    
    # Send
    sync_res = await chat_handler.send_message(message)
    assert sync_res["content"] == "100"
    assert sync_res["model"] == "calculator"
    
    # Stream
    stream_events = await gather_stream(chat_handler.stream_message(message))
    tokens = [e["value"] for e in stream_events if e["type"] == "token"]
    assert "".join(tokens) == "100"
    
    done_event = next(e for e in stream_events if e["type"] == "done")
    assert done_event["model"] == "calculator"

@pytest.mark.asyncio
async def test_memory_commands_parity(chat_handler):
    message = "forget that I like Python."
    chat_handler.preference_engine.remove_explicit_preference.return_value = True
    
    # Send
    sync_res = await chat_handler.send_message(message)
    assert "Forgotten." in sync_res["content"]
    assert sync_res["model"] == "memory_parser"
    
    # Stream
    stream_events = await gather_stream(chat_handler.stream_message(message))
    tokens = [e["value"] for e in stream_events if e["type"] == "token"]
    assert "".join(tokens) == "Forgotten."

@pytest.mark.asyncio
async def test_trust_layer_parity(chat_handler):
    class MockPermDecision:
        def __init__(self, allowed):
            self.allowed = allowed
            
    chat_handler.perms.check.return_value = MockPermDecision(False)
    message = "Do something bad"
    
    # Send
    sync_res = await chat_handler.send_message(message)
    assert "blocked by trust layer" in sync_res["content"].lower()
    
    # Stream
    stream_events = await gather_stream(chat_handler.stream_message(message))
    tokens = [e["value"] for e in stream_events if e["type"] == "token"]
    assert "blocked by trust layer" in "".join(tokens).lower()

@pytest.mark.asyncio
async def test_forecaster_intents_parity(chat_handler):
    message = "Forecast the next 5 values for 1, 2, 3, 4, 5"
    with patch("modules.execution_sandbox.src.forecaster.TimesFMForecaster") as mock_forecaster_cls:
        mock_instance = MagicMock()
        mock_instance.forecast.return_value = {
            "success": True,
            "forecast": [6, 7, 8, 9, 10],
            "lower_bound": [5, 6, 7, 8, 9],
            "upper_bound": [7, 8, 9, 10, 11],
            "metrics": {"volatility": 0.5},
            "ascii_chart": "chart"
        }
        mock_forecaster_cls.return_value = mock_instance
        
        # Send
        sync_res = await chat_handler.send_message(message)
        assert sync_res["content"] == "Router Response"
        
        # Stream
        stream_events = await gather_stream(chat_handler.stream_message(message))
        tokens = [e["value"] for e in stream_events if e["type"] == "token"]
        assert "".join(tokens) == "Router Response"

@pytest.mark.asyncio
async def test_browser_intents_parity(chat_handler):
    message = "go to https://example.com"
    chat_handler.browser.goto = AsyncMock(return_value={"success": True})
    chat_handler.browser.extract_text = AsyncMock(return_value="Example Domain Content")
    
    # Browser doesn't early-return, it modifies the intent and routes
    sync_res = await chat_handler.send_message(message)
    assert sync_res["content"] == "Router Response"
    
    # Stream
    stream_events = await gather_stream(chat_handler.stream_message(message))
    tokens = [e["value"] for e in stream_events if e["type"] == "token"]
    assert "".join(tokens) == "Router Response"
    
    # Check that goto was called twice (once for sync, once for stream)
    assert chat_handler.browser.goto.call_count == 2

@pytest.mark.asyncio
async def test_standard_routing_parity(chat_handler):
    message = "Hello world"
    
    # Send
    sync_res = await chat_handler.send_message(message)
    assert sync_res["content"] == "Router Response"
    
    # Stream
    stream_events = await gather_stream(chat_handler.stream_message(message))
    tokens = [e["value"] for e in stream_events if e["type"] == "token"]
    assert "".join(tokens) == "Router Response"

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_vision_fallback_parity(mock_acompletion, chat_handler):
    class MockMessage:
        content = "Vision Description"
    class MockChoice:
        message = MockMessage()
    class MockResponse:
        choices = [MockChoice()]
        
    mock_acompletion.return_value = MockResponse()
    chat_handler._ensure_ollama_model = AsyncMock()
    
    message = "What is in this image?"
    images = ["data:image/png;base64,..."]
    
    # Send
    sync_res = await chat_handler.send_message(message, images=images)
    assert sync_res["content"] == "Router Response"
    assert chat_handler._ensure_ollama_model.call_count == 1
    
    # Stream
    stream_events = await gather_stream(chat_handler.stream_message(message, images=images))
    tokens = [e["value"] for e in stream_events if e["type"] == "token"]
    assert "".join(tokens) == "Router Response"
    assert chat_handler._ensure_ollama_model.call_count == 2

@pytest.mark.asyncio
async def test_send_message_conversation_id_generation(chat_handler):
    message = "Hello"
    sync_res = await chat_handler.send_message(message)
    assert sync_res.get("conversation_id") is not None
    assert sync_res["conversation_id"].startswith("conv_")

@pytest.mark.asyncio
async def test_stream_message_conversation_id_generation(chat_handler):
    message = "Hello"
    stream_events = await gather_stream(chat_handler.stream_message(message))
    done_event = next((e for e in stream_events if e["type"] == "done"), None)
    assert done_event is not None
    assert done_event.get("conversation_id") is not None
    assert done_event["conversation_id"].startswith("conv_")
