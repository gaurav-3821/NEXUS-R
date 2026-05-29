from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger("nexus-r.identity")


class IdentityStore:
    """Encrypted local identity and preference persistence layer.
    
    Uses AES-256 symmetric encryption (Fernet) to store user identity,
    explicit memories, and inferred behavioral preferences at rest.
    Supports temporal decay for inferred preferences.
    """

    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = self.state_dir / "identity.key"
        self.data_path = self.state_dir / "identity.enc"
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        return key

    def read(self) -> dict[str, Any]:
        """Read and decrypt the full identity store."""
        if not self.data_path.exists():
            return {}
        try:
            payload = self._fernet.decrypt(self.data_path.read_bytes())
            return json.loads(payload.decode("utf-8"))
        except Exception as e:
            logger.error("Failed to read identity store: %s", e)
            return {}

    def write(self, data: dict[str, Any]) -> None:
        """Encrypt and persist the identity store."""
        try:
            token = self._fernet.encrypt(json.dumps(data).encode("utf-8"))
            self.data_path.write_bytes(token)
        except Exception as e:
            logger.error("Failed to write identity store: %s", e)

    # --- Explicit Memories ---

    def get_memories(self) -> list[str]:
        data = self.read()
        return data.get("memories", [])

    def add_memory(self, memory: str) -> None:
        data = self.read()
        memories = data.get("memories", [])
        if memory not in memories:
            memories.append(memory)
            data["memories"] = memories
            self.write(data)

    def remove_memory(self, index: int) -> bool:
        data = self.read()
        memories = data.get("memories", [])
        if 0 <= index < len(memories):
            memories.pop(index)
            data["memories"] = memories
            self.write(data)
            return True
        return False

    # --- Simple Key-Value Preferences ---

    def get_preferences(self) -> dict[str, str]:
        data = self.read()
        return data.get("preferences", {})

    def set_preference(self, key: str, value: str) -> None:
        data = self.read()
        prefs = data.get("preferences", {})
        prefs[key] = value
        data["preferences"] = prefs
        self.write(data)

    # --- Inferred Preferences with Temporal Metadata ---

    def add_inferred_preference(
        self, key: str, value: str, confidence: float
    ) -> None:
        """Add or reinforce an inferred behavioral preference.
        
        If the key already exists, reinforces it by blending confidence
        scores and incrementing the reinforcement counter.
        """
        data = self.read()
        inferred = data.get("inferred_preferences", {})
        now = time.time()

        if key in inferred and isinstance(inferred[key], dict):
            existing = inferred[key]
            existing["confidence"] = min(
                1.0, existing.get("confidence", 0.5) * 0.7 + confidence * 0.3
            )
            existing["reinforced_at"] = now
            existing["reinforcement_count"] = (
                existing.get("reinforcement_count", 0) + 1
            )
            existing["value"] = value
        else:
            inferred[key] = {
                "value": value,
                "confidence": round(confidence, 4),
                "created_at": now,
                "reinforced_at": now,
                "reinforcement_count": 1,
            }

        data["inferred_preferences"] = inferred
        self.write(data)

    def get_active_preferences(
        self, decay_half_life_days: float = 14.0
    ) -> dict[str, Any]:
        """Return inferred preferences with temporal decay applied.
        
        Memory strength decays exponentially: effective = confidence × 0.5^(age/half_life).
        Preferences below 0.25 effective confidence are filtered out.
        """
        data = self.read()
        inferred = data.get("inferred_preferences", {})
        now = time.time()
        active: dict[str, Any] = {}

        for key, meta in inferred.items():
            if not isinstance(meta, dict):
                # Legacy format (plain string) — migrate
                active[key] = {
                    "value": str(meta),
                    "effective_confidence": 0.5,
                    "age_days": 0.0,
                    "reinforcement_count": 0,
                }
                continue

            reinforced_at = meta.get("reinforced_at", meta.get("created_at", now))
            age_days = (now - reinforced_at) / 86400.0
            decay = 0.5 ** (age_days / max(decay_half_life_days, 0.1))
            effective = meta.get("confidence", 0.5) * decay

            if effective >= 0.25:
                active[key] = {
                    "value": meta.get("value", ""),
                    "effective_confidence": round(effective, 3),
                    "age_days": round(age_days, 1),
                    "reinforcement_count": meta.get("reinforcement_count", 0),
                }

        return active

    def delete_inferred_preference(self, key: str) -> bool:
        """Delete a specific inferred preference."""
        data = self.read()
        inferred = data.get("inferred_preferences", {})
        if key in inferred:
            del inferred[key]
            data["inferred_preferences"] = inferred
            self.write(data)
            return True
        return False

    def clear_inferred_preferences(self) -> None:
        """Clear all inferred preferences."""
        data = self.read()
        data["inferred_preferences"] = {}
        self.write(data)

    # --- Full Data Access ---

    def get_all_structured(self) -> dict[str, Any]:
        """Return complete identity data for inspection/export."""
        data = self.read()
        return {
            "memories": data.get("memories", []),
            "preferences": data.get("preferences", {}),
            "explicit_preferences": data.get("explicit_preferences", []),
            "inferred_preferences": data.get("inferred_preferences", {}),
        }
