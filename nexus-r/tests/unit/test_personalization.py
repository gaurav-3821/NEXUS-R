import pytest
import os
import json
from pathlib import Path
from modules.input_gateway.src.memory_parser import MemoryParser
from modules.web_ui.src.preference_engine import PreferenceEngine
from modules.web_ui.src.pattern_store import PatternStore
from modules.state_core.src.behavior_tracker import BehaviorTracker
from modules.execution_sandbox.src.calculator import SafeCalculator
from modules.state_core.src.identity_store import IdentityStore

@pytest.fixture
def temp_identity_store(tmp_path):
    store = IdentityStore(tmp_path / "identity")
    # Initialize empty
    store.write({"explicit_preferences": [], "inferred_preferences": {}})
    return store

def test_memory_parser():
    parser = MemoryParser()
    
    # Test Remember
    res = parser.parse("Remember: always output python code")
    assert res == {"action": "remember", "content": "always output python code"}
    
    res = parser.parse("note that I like short answers")
    assert res == {"action": "remember", "content": "I like short answers"}
    
    # Test Forget
    res = parser.parse("Forget: always output python code")
    assert res == {"action": "forget", "content": "always output python code"}
    
    res = parser.parse("forget that I like short answers")
    assert res == {"action": "forget", "content": "I like short answers"}
    
    # Test List
    res = parser.parse("What do you remember about me?")
    assert res == {"action": "list", "content": ""}
    
    # Test None
    res = parser.parse("What is the weather?")
    assert res is None

def test_preference_engine(temp_identity_store):
    engine = PreferenceEngine(temp_identity_store)
    
    # Empty initially
    assert engine.get_system_prompt_additions() == ""
    
    # Add explicit
    engine.add_explicit_preference("Prefer python")
    additions = engine.get_system_prompt_additions()
    assert "Prefer python" in additions
    assert "[USER PREFERENCES]" in additions
    
    # Add inferred (simulate behavior tracker)
    data = temp_identity_store.read()
    data["inferred_preferences"] = {"style": "concise"}
    temp_identity_store.write(data)
    
    additions = engine.get_system_prompt_additions()
    assert "Prefer python" in additions
    assert "style: concise" in additions
    
    # Remove explicit
    assert engine.remove_explicit_preference("prefer python") is True
    assert "Prefer python" not in engine.get_system_prompt_additions()

def test_pattern_store(tmp_path):
    store = PatternStore(tmp_path)
    
    # Empty initially
    assert store.match("how to do integral") is None
    
    # Extract and save
    store.extract_and_save("how to do an integral of x^2", "First, use the power rule...")
    
    # Match
    match = store.match("integral of x^3")
    assert match is not None
    assert match["topic"] == "math"
    assert match["method"] == "step-by-step"
    
    # Injection prompt
    prompt = store.get_prompt_injection(match)
    assert "[PATTERN MATCH]" in prompt
    assert "math" in prompt

def test_behavior_tracker(temp_identity_store):
    tracker = BehaviorTracker(temp_identity_store)
    
    # Test Confused -> Simplify
    for _ in range(15):
        tracker.record_signal("scroll_event", 1)
    tracker.record_signal("time_on_answer", 300)
    for _ in range(3):
        tracker.record_signal("interrupted", 1)
    
    data = temp_identity_store.read()
    assert "inferred_preferences" in data
    assert "complexity" in data["inferred_preferences"]
    assert "simplify" in data["inferred_preferences"]["complexity"]["value"]
    
    # Test wants concise
    for _ in range(5):
        tracker.record_signal("copy", "E=mc^2")
    
    data = temp_identity_store.read()
    assert "style" in data["inferred_preferences"]
    assert "concise" in data["inferred_preferences"]["style"]["value"]
    
    # Test wants derivation
    for _ in range(5):
        tracker.record_signal("follow_up", "why did you do that?")
    
    data = temp_identity_store.read()
    assert "depth" in data["inferred_preferences"]
    assert "deep technical derivations" in data["inferred_preferences"]["depth"]["value"]

@pytest.mark.parametrize("expr, expected", [
    ("2 + 2", "4"),
    ("456 * 4", "1824"),
    ("sqrt(16)", "4"),
    ("2^3", "8"),
    ("10 / 2", "5"),
    ("(2+3)*4", "20"),
    ("0 * 10", "0"),
    ("100 - 50", "50"),
    ("3^2", "9"),
    ("2.5 * 2", "5"),
    ("10.5 + 0.5", "11"),
    ("1/2", "0.5"),
    ("sqrt(25)", "5"),
    ("sqrt(100)", "10"),
    ("10 % 3", "1"),
    ("5 % 2", "1"),
    ("15 - 5 * 2", "5"),
    ("(15 - 5) * 2", "20"),
    ("-5 + 10", "5"),
    ("10 + -5", "5"),
    ("-(2+3)", "-5"),
    ("sqrt(9)", "3"),
    ("2^4", "16"),
    ("100 / 25", "4"),
    ("50 * 0.5", "25"),
    ("10 + 20 + 30", "60")
])
def test_safe_calculator_valid(expr, expected):
    calc = SafeCalculator()
    assert calc.evaluate(expr) == expected

@pytest.mark.parametrize("expr", [
    "What is 2+2?",
    "explain 456*4",
    "import os",
    "eval('2+2')",
    "sys.exit(1)",
    "open('file.txt')",
    "2 + two",
    "sqrt(-16)",
    "math.sqrt(16)"
])
def test_safe_calculator_invalid(expr):
    calc = SafeCalculator()
    assert calc.evaluate(expr) is None
