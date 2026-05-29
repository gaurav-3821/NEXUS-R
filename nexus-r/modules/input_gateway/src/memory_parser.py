import re
from typing import Any

class MemoryParser:
    def __init__(self):
        # Basic patterns to catch explicit memory instructions
        self.remember_pat = re.compile(r"^(?:remember|always|note that)\s*(?:[:]+\s*|that\s+)?(.+)$", re.IGNORECASE)
        self.forget_pat = re.compile(r"^(?:forget)\s*(?:[:]+\s*|that\s+)?(.+)$", re.IGNORECASE)
        self.list_pat = re.compile(r"^(?:what do you remember about me\?*|list memory|show preferences)$", re.IGNORECASE)

    def parse(self, user_input: str) -> dict[str, str] | None:
        """Parse user input to detect explicit memory commands."""
        clean_input = user_input.strip()
        
        if self.list_pat.match(clean_input):
            return {"action": "list", "content": ""}
            
        rem_match = self.remember_pat.match(clean_input)
        if rem_match:
            return {"action": "remember", "content": rem_match.group(1).strip()}
            
        forg_match = self.forget_pat.match(clean_input)
        if forg_match:
            return {"action": "forget", "content": forg_match.group(1).strip()}
            
        return None
