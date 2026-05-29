import json
import time
from uuid import uuid4
from pathlib import Path
from typing import Any

class PatternStore:
    def __init__(self, workspace_root: str):
        self.store_path = Path(workspace_root) / ".nexus-r" / "patterns.json"
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                self.patterns = json.loads(self.store_path.read_text())
            except json.JSONDecodeError:
                self.patterns = []
        else:
            self.patterns = []

    def _save(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self.patterns, indent=2))

    def extract_and_save(self, query: str, response: str) -> None:
        """Extract pattern from successful cloud response and save as template."""
        # Simple heuristic extraction
        topic = "general"
        if "physics" in query.lower() or "force" in query.lower():
            topic = "physics"
        elif "math" in query.lower() or "integral" in query.lower() or "derivative" in query.lower():
            topic = "math"
            
        method = "direct"
        if "step 1" in response.lower() or "first," in response.lower():
            method = "step-by-step"
        elif "analogy" in response.lower() or "imagine" in response.lower():
            method = "analogy"
            
        pattern = {
            "pattern_id": str(uuid4()),
            "query_keywords": [w for w in query.lower().split() if len(w) > 4][:5],
            "topic": topic,
            "method": method,
            "template_preview": response[:200] + "...",  # Store prefix as template hint
            "success_count": 1,
            "last_used": time.time()
        }
        self.patterns.append(pattern)
        self._save()

    def match(self, query: str) -> dict[str, Any] | None:
        """Find matching pattern for query to inject into local prompt."""
        query_words = set(query.lower().split())
        best_match = None
        best_score = 0
        
        for p in self.patterns:
            score = sum(1 for kw in p["query_keywords"] if kw in query_words)
            if score > 0 and score > best_score:
                best_score = score
                best_match = p
                
        if best_match and best_score >= 1: # Arbitrary threshold
            best_match["success_count"] += 1
            best_match["last_used"] = time.time()
            self._save()
            return best_match
            
        return None
        
    def get_prompt_injection(self, pattern: dict[str, Any]) -> str:
        return f"\n[PATTERN MATCH] Previously successful approach for this type of query: Topic: {pattern['topic']}, Method: {pattern['method']}. Please follow this structure."
