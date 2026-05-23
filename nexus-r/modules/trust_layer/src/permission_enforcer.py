from __future__ import annotations

from nexus_r.events import Action, PermissionDecision, PermissionTier


class PermissionEnforcer:
    TIER_ACTIONS = {
        PermissionTier.T1: {"list_files", "read_file", "search_text", "general_llm", "view_history", "view_cost"},
        PermissionTier.T2: {
            "list_files",
            "read_file",
            "search_text",
            "general_llm",
            "write_file",
            "append_file",
            "run_terminal",
            "view_history",
            "view_cost",
        },
    }

    def check(self, action: Action, tier: PermissionTier) -> PermissionDecision:
        if tier in {PermissionTier.T3, PermissionTier.T4}:
            return PermissionDecision(
                allowed=False,
                tier=tier,
                reason=f"{tier.value} is not implemented in Phase 1.",
                redacted_metadata=self._redact(action.metadata),
            )
        allowed_actions = self.TIER_ACTIONS.get(tier, set())
        if action.name in allowed_actions:
            return PermissionDecision(
                allowed=True,
                tier=tier,
                reason=f"{action.name} allowed under {tier.value}.",
                redacted_metadata=self._redact(action.metadata),
            )
        return PermissionDecision(
            allowed=False,
            tier=tier,
            reason=f"{action.name} is not permitted under {tier.value}.",
            redacted_metadata=self._redact(action.metadata),
        )

    def _redact(self, metadata: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, value in metadata.items():
            if "secret" in key or "token" in key or "key" in key:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = value
        return redacted
