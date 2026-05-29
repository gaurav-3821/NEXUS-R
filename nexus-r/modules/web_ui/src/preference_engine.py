from typing import Any

class PreferenceEngine:
    def __init__(self, identity_store):
        self.identity_store = identity_store

    def get_system_prompt_additions(self) -> str:
        """Combine explicit and inferred preferences into a system prompt block."""
        data = self.identity_store.read()
        
        explicit = data.get("explicit_preferences", [])
        
        # Use new temporally decayed active preferences
        inferred_active = self.identity_store.get_active_preferences()
        
        if not explicit and not inferred_active:
            return ""
            
        prompt_parts = ["\n[USER PREFERENCES]"]
        
        if explicit:
            prompt_parts.append("Explicit instructions from user:")
            for pref in explicit:
                prompt_parts.append(f"- {pref}")
                
        if inferred_active:
            prompt_parts.append("Inferred behavioral preferences:")
            # Sort by confidence descending
            sorted_inferred = sorted(
                inferred_active.items(),
                key=lambda x: x[1].get("effective_confidence", 0),
                reverse=True
            )
            for k, meta in sorted_inferred:
                prompt_parts.append(f"- {k}: {meta.get('value')} (confidence: {meta.get('effective_confidence', 0):.2f})")
                
        prompt_parts.append("[/USER PREFERENCES]\n")
        return "\n".join(prompt_parts)

    def add_explicit_preference(self, content: str) -> None:
        data = self.identity_store.read()
        prefs = data.get("explicit_preferences", [])
        if content not in prefs:
            prefs.append(content)
            data["explicit_preferences"] = prefs
            self.identity_store.write(data)

    def remove_explicit_preference(self, content: str) -> bool:
        data = self.identity_store.read()
        prefs = data.get("explicit_preferences", [])
        
        # Simple match for removal
        new_prefs = [p for p in prefs if content.lower() not in p.lower()]
        if len(new_prefs) != len(prefs):
            data["explicit_preferences"] = new_prefs
            self.identity_store.write(data)
            return True
        return False
        
    def get_all_preferences_formatted(self) -> str:
        data = self.identity_store.read()
        explicit = data.get("explicit_preferences", [])
        inferred = self.identity_store.get_active_preferences()
        
        if not explicit and not inferred:
            return "I don't have any specific preferences saved for you yet."
            
        lines = []
        if explicit:
            lines.append("Explicitly remembered:")
            for p in explicit:
                lines.append(f"- {p}")
        if inferred:
            lines.append("Inferred from behavior (active):")
            for k, meta in inferred.items():
                lines.append(f"- {k}: {meta.get('value')}")
        return "\n".join(lines)
