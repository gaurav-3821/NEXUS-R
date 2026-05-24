from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from nexus_r.events import Action, PermissionDecision, PermissionTier

logger = logging.getLogger(__name__)


class ApprovalVerdict(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"


@dataclass
class ApprovalRequest:
    action: Action
    tier: PermissionTier
    reason: str
    verdict: ApprovalVerdict = ApprovalVerdict.PENDING
    documented_reason: str = ""


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
        PermissionTier.T3: {
            "http_get",
            "read_env",
            "read_clipboard",
            "run_terminal",
            "read_external_file",
            "view_history",
            "view_cost",
        },
        PermissionTier.T4: {
            "http_post",
            "http_put",
            "http_delete",
            "deploy",
            "install",
            "delete_file_outside_workspace",
            "config_write",
            "modify_config",
            "write_external_file",
            "browser_action",
            "run_arbitrary_command",
            "financial_transaction",
        },
    }

    APPROVAL_REQUIRED = {
        PermissionTier.T3: "prompt",
        PermissionTier.T4: "explicit",
    }

    def __init__(self, approval_callback: Any | None = None) -> None:
        self._approval_callback = approval_callback or self._default_approval_prompt
        self._pending_approvals: dict[str, ApprovalRequest] = {}

    async def check(
        self,
        action: Action,
        tier: PermissionTier,
        risk_score: float | None = None,
        risk_verdict: str | None = None,
    ) -> PermissionDecision:
        allowed_actions = self.TIER_ACTIONS.get(tier, set())
        if action.name not in allowed_actions:
            return PermissionDecision(
                allowed=False,
                tier=tier,
                reason=f"{action.name} is not permitted under {tier.value}.",
                redacted_metadata=self._redact(action.metadata),
            )

        if tier == PermissionTier.T3:
            return await self._handle_t3(action)
        elif tier == PermissionTier.T4:
            return await self._handle_t4(action, risk_score, risk_verdict)

        if risk_verdict == "deny":
            return PermissionDecision(
                allowed=False,
                tier=tier,
                reason=f"Risk classifier denied {action.name}.",
                redacted_metadata=self._redact(action.metadata),
            )

        return PermissionDecision(
            allowed=True,
            tier=tier,
            reason=f"{action.name} allowed under {tier.value}.",
            redacted_metadata=self._redact(action.metadata),
        )

    async def _handle_t3(self, action: Action) -> PermissionDecision:
        approved = await self._approval_callback(action, PermissionTier.T3)
        if approved:
            return PermissionDecision(
                allowed=True,
                tier=PermissionTier.T3,
                reason=f"{action.name} approved via user prompt under T3.",
                redacted_metadata=self._redact(action.metadata),
            )
        return PermissionDecision(
            allowed=False,
            tier=PermissionTier.T3,
            reason=f"T3 action {action.name} requires user prompt — denied by user.",
            redacted_metadata=self._redact(action.metadata),
        )

    async def _handle_t4(
        self,
        action: Action,
        risk_score: float | None = None,
        risk_verdict: str | None = None,
    ) -> PermissionDecision:
        if risk_verdict == "deny":
            return PermissionDecision(
                allowed=False,
                tier=PermissionTier.T4,
                reason=f"Risk classifier denied {action.name} (score={risk_score}).",
                redacted_metadata=self._redact(action.metadata),
            )

        approval = await self._approval_callback(action, PermissionTier.T4)
        if not approval:
            return PermissionDecision(
                allowed=False,
                tier=PermissionTier.T4,
                reason=f"T4 action {action.name} requires explicit confirmation — denied by user.",
                redacted_metadata=self._redact(action.metadata),
            )

        if isinstance(approval, str):
            self._pending_approvals[id(action)] = ApprovalRequest(
                action=action,
                tier=PermissionTier.T4,
                reason=action.name,
                verdict=ApprovalVerdict.APPROVED,
                documented_reason=approval,
            )

        return PermissionDecision(
            allowed=True,
            tier=PermissionTier.T4,
            reason=f"T4 action {action.name} approved with documented reason.",
            redacted_metadata=self._redact(action.metadata),
        )

    async def _default_approval_prompt(self, action: Action, tier: PermissionTier) -> bool:
        tier_label = tier.value
        print(f"\n[{tier_label}] Action: {action.name}")
        if action.target:
            print(f"  Target: {action.target}")
        print(f"  Reason: {tier_label} requires your approval")

        if tier == PermissionTier.T4:
            print("  You must document a reason for this action.")
            documented_reason = input("  Reason: ").strip()
            if not documented_reason:
                print("  T4 actions require a documented reason.")
                return False
            return documented_reason

        response = input(f"  Approve {tier_label} action? (y/N): ").strip().lower()
        return response == "y"

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        return [req for req in self._pending_approvals.values() if req.verdict == ApprovalVerdict.PENDING]

    def get_approval_history(self) -> list[ApprovalRequest]:
        return list(self._pending_approvals.values())

    def _redact(self, metadata: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, value in metadata.items():
            if "secret" in key or "token" in key or "key" in key:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = value
        return redacted
