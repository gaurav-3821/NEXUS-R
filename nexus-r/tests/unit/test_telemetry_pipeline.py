import pytest

from modules.state_core.src.behavior_tracker import BehaviorTracker

class DummyIdentityStore:
    def __init__(self):
        self.inferred = {}
        
    def add_inferred_preference(self, key, value, confidence):
        self.inferred[key] = {"value": value, "confidence": confidence}


def test_behavior_tracker_initialization():
    store = DummyIdentityStore()
    tracker = BehaviorTracker(store)
    
    assert tracker.session_signals["time_on_answer"] == 0.0
    assert tracker.session_signals["scroll_events"] == 0
    assert len(tracker.session_signals["copied_text"]) == 0

def test_record_signals_and_inference():
    store = DummyIdentityStore()
    tracker = BehaviorTracker(store)
    
    # Simulate a confused user
    for _ in range(20):
        tracker.record_signal("scroll_event", 1)
        
    tracker.record_signal("time_on_answer", 400)
    tracker.record_signal("interrupted", 1)
    tracker.record_signal("regenerated", 1)
    
    scores = tracker._compute_inference_scores()
    
    # High confusion score expected
    assert scores["confusion"] > 0.6
    
    # Should have triggered analysis since > MINIMUM_DATA_POINTS
    assert "confusion" in store.inferred
    assert store.inferred["confusion"]["confidence"] > 0.5
    assert "simplify explanations" in store.inferred["confusion"]["value"]

def test_technical_depth_inference():
    store = DummyIdentityStore()
    tracker = BehaviorTracker(store)
    
    # Simulate a technical user
    tracker.record_signal("copy", "def my_func():")
    tracker.record_signal("copy", "class MyModel:")
    tracker.record_signal("copy", "import os")
    
    tracker.record_signal("follow_up", "Why does this happen?")
    tracker.record_signal("follow_up", "How can I fix it?")
    
    scores = tracker._compute_inference_scores()
    
    assert scores["technical_depth"] > 0.4
    
    tracker._analyze_and_infer() # Force inference as accumulator needs 2 passes
    tracker._analyze_and_infer()
    
    assert "technical_depth" in store.inferred

def test_conciseness_inference():
    store = DummyIdentityStore()
    tracker = BehaviorTracker(store)
    
    # Simulate math user
    tracker.record_signal("copy", "x = y + 2")
    tracker.record_signal("copy", "E = mc^2")
    tracker.record_signal("copy", "Σ(x)")
    
    scores = tracker._compute_inference_scores()
    assert scores["conciseness"] > 0.5
