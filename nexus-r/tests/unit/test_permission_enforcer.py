from __future__ import annotations

import unittest.mock
from unittest.mock import AsyncMock

import pytest

from nexus_r.events import Action, PermissionTier
from modules.trust_layer.src.permission_enforcer import (
    ApprovalVerdict,
    PermissionEnforcer,
)


class TestT1T2Permissions:
    @pytest.mark.asyncio
    async def test_t1_allows_read_actions(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="read_file", tier=PermissionTier.T1),
            PermissionTier.T1,
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_t1_denies_write_actions(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="write_file", tier=PermissionTier.T1),
            PermissionTier.T1,
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_t2_allows_write_actions(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="write_file", tier=PermissionTier.T2),
            PermissionTier.T2,
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_t2_allows_terminal(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="run_terminal", tier=PermissionTier.T2),
            PermissionTier.T2,
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_t2_denies_external_read(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="http_get", tier=PermissionTier.T2),
            PermissionTier.T2,
        )
        assert decision.allowed is False


class TestT3Permissions:
    @pytest.mark.asyncio
    async def test_t3_requires_user_prompt(self):
        mock_approval = AsyncMock(return_value=True)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="http_get", tier=PermissionTier.T3, target="https://example.com"),
            PermissionTier.T3,
        )
        assert decision.allowed is True
        assert "approved via user prompt" in decision.reason
        mock_approval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_t3_denied_when_user_rejects(self):
        mock_approval = AsyncMock(return_value=False)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="read_env", tier=PermissionTier.T3),
            PermissionTier.T3,
        )
        assert decision.allowed is False
        assert "denied by user" in decision.reason

    @pytest.mark.asyncio
    async def test_t3_denies_not_in_tier_actions(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="deploy", tier=PermissionTier.T3),
            PermissionTier.T3,
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_t3_allows_read_clipboard_with_approval(self):
        mock_approval = AsyncMock(return_value=True)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="read_clipboard", tier=PermissionTier.T3),
            PermissionTier.T3,
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_t3_read_external_file_requires_prompt(self):
        mock_approval = AsyncMock(return_value=True)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="read_external_file", tier=PermissionTier.T3, target="/etc/hosts"),
            PermissionTier.T3,
        )
        assert decision.allowed is True
        mock_approval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_t3_action_not_in_allowlist_denied_even_with_approval(self):
        mock_approval = AsyncMock(return_value=True)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="deploy", tier=PermissionTier.T3),
            PermissionTier.T3,
        )
        assert decision.allowed is False


class TestT4Permissions:
    @pytest.mark.asyncio
    async def test_t4_requires_explicit_confirmation_with_reason(self):
        documented_reason = "Need to deploy hotfix to production"
        mock_approval = AsyncMock(return_value=documented_reason)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="deploy", tier=PermissionTier.T4, target="production"),
            PermissionTier.T4,
        )
        assert decision.allowed is True
        assert "approved with documented reason" in decision.reason
        mock_approval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_t4_denied_when_user_rejects(self):
        mock_approval = AsyncMock(return_value=False)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="install", tier=PermissionTier.T4),
            PermissionTier.T4,
        )
        assert decision.allowed is False
        assert "denied by user" in decision.reason

    @pytest.mark.asyncio
    async def test_t4_no_auto_approval(self):
        mock_approval = AsyncMock(return_value=False)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="http_post", tier=PermissionTier.T4, target="https://unknown.example.com"),
            PermissionTier.T4,
        )
        assert decision.allowed is False
        mock_approval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_t4_denied_if_action_not_in_allowlist(self):
        mock_approval = AsyncMock(return_value=True)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="read_file", tier=PermissionTier.T4),
            PermissionTier.T4,
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_t4_risk_denial_overrides(self):
        mock_approval = AsyncMock(return_value=True)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        decision = await enforcer.check(
            Action(name="http_post", tier=PermissionTier.T4, target="https://evil.example.com"),
            PermissionTier.T4,
            risk_score=1.0,
            risk_verdict="deny",
        )
        assert decision.allowed is False
        assert "Risk classifier denied" in decision.reason
        mock_approval.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_t4_denies_actions_not_in_tier(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="read_file", tier=PermissionTier.T4),
            PermissionTier.T4,
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_t4_approval_stores_documented_reason(self):
        reason = "Urgent security patch for CVE-2024-1234"
        mock_approval = AsyncMock(return_value=reason)
        enforcer = PermissionEnforcer(approval_callback=mock_approval)
        action = Action(name="deploy", tier=PermissionTier.T4, target="staging")
        decision = await enforcer.check(action, PermissionTier.T4)
        assert decision.allowed is True
        assert enforcer.get_approval_history()
        entry = enforcer.get_approval_history()[-1]
        assert entry.documented_reason == reason


class TestT1T2RiskOverride:
    @pytest.mark.asyncio
    async def test_t1_action_denied_by_risk_classifier(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="read_file", tier=PermissionTier.T1),
            PermissionTier.T1,
            risk_verdict="deny",
            risk_score=0.95,
        )
        assert decision.allowed is False
        assert "Risk classifier denied" in decision.reason

    @pytest.mark.asyncio
    async def test_t2_action_denied_by_risk_classifier(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(name="write_file", tier=PermissionTier.T2),
            PermissionTier.T2,
            risk_verdict="deny",
            risk_score=0.8,
        )
        assert decision.allowed is False
        assert "Risk classifier denied" in decision.reason


class TestApprovalPrompt:
    @pytest.mark.asyncio
    async def test_default_approval_t4_empty_reason_denied(self):
        with unittest.mock.patch("builtins.input", return_value=""):
            enforcer = PermissionEnforcer()
            approved = await enforcer._default_approval_prompt(
                Action(name="deploy", tier=PermissionTier.T4, target="prod"),
                PermissionTier.T4,
            )
            assert approved is False

    @pytest.mark.asyncio
    async def test_default_approval_t3_yes_approved(self):
        with unittest.mock.patch("builtins.input", return_value="y"):
            enforcer = PermissionEnforcer()
            approved = await enforcer._default_approval_prompt(
                Action(name="http_get", tier=PermissionTier.T3, target="https://example.com"),
                PermissionTier.T3,
            )
            assert approved is True

    @pytest.mark.asyncio
    async def test_default_approval_t3_no_denied(self):
        with unittest.mock.patch("builtins.input", return_value="n"):
            enforcer = PermissionEnforcer()
            approved = await enforcer._default_approval_prompt(
                Action(name="read_env", tier=PermissionTier.T3),
                PermissionTier.T3,
            )
            assert approved is False

    def test_get_pending_approvals_empty(self):
        enforcer = PermissionEnforcer()
        assert enforcer.get_pending_approvals() == []


class TestRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secrets_in_metadata(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(
                name="read_file",
                tier=PermissionTier.T1,
                metadata={"api_key": "sk-1234", "path": "file.txt"},
            ),
            PermissionTier.T1,
        )
        assert decision.redacted_metadata["api_key"] == "***REDACTED***"
        assert decision.redacted_metadata["path"] == "file.txt"

    @pytest.mark.asyncio
    async def test_redacts_tokens_and_keys(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(
                name="list_files",
                tier=PermissionTier.T1,
                metadata={"token": "ghp_xxxx", "auth_key": "abc123"},
            ),
            PermissionTier.T1,
        )
        assert decision.redacted_metadata["token"] == "***REDACTED***"
        assert decision.redacted_metadata["auth_key"] == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_redacted_metadata_in_denied_decision(self):
        enforcer = PermissionEnforcer()
        decision = await enforcer.check(
            Action(
                name="write_file",
                tier=PermissionTier.T1,
                metadata={"secret": "topsecret", "name": "test.txt"},
            ),
            PermissionTier.T1,
        )
        assert decision.allowed is False
        assert decision.redacted_metadata["secret"] == "***REDACTED***"
