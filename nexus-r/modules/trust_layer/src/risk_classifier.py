from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nexus_r.events import PermissionTier

logger = logging.getLogger(__name__)

SENSITIVE_PATHS = [
    re.compile(r"[\\/]etc[\\/]"),
    re.compile(r"[\\/]Windows[\\/]System32[\\/]"),
    re.compile(r"[\\/]\.ssh[\\/]"),
    re.compile(r"[\\/]\.aws[\\/]"),
    re.compile(r"[\\/]\.config[\\/]"),
]

DESTRUCTIVE_COMMANDS = [
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bformat\b", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fFsS]", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
]

NETWORK_COMMANDS = [
    re.compile(r"\bcurl\b", re.IGNORECASE),
    re.compile(r"\bwget\b", re.IGNORECASE),
    re.compile(r"\bInvoke-WebRequest\b", re.IGNORECASE),
    re.compile(r"\bnet\s+(use|send|share)\b", re.IGNORECASE),
]

SECRET_VAR_PATTERNS = [
    re.compile(r"API_KEY", re.IGNORECASE),
    re.compile(r"SECRET", re.IGNORECASE),
    re.compile(r"PASSWORD", re.IGNORECASE),
    re.compile(r"TOKEN", re.IGNORECASE),
    re.compile(r"CREDENTIAL", re.IGNORECASE),
]

ORIGIN_ALLOWLIST = {
    "api.github.com",
    "api.openai.com",
    "api.anthropic.com",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
}


@dataclass
class RiskScore:
    verdict: str
    score: float
    reasons: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)


@dataclass
class RiskRule:
    rule_id: str
    condition: str
    verdict: str
    score: float
    reason_template: str


@dataclass
class TierHistoryEntry:
    action_type: str
    target: str
    timestamp: datetime
    success: bool
    tier: PermissionTier


DEFAULT_RULES: list[RiskRule] = [
    RiskRule(rule_id="R1", condition="action == 'delete_file' and _is_outside_workspace(target)",
             verdict="deny", score=1.0, reason_template="Destructive cross-boundary write"),
    RiskRule(rule_id="R2", condition="_matches_sensitive_path(target)",
             verdict="deny", score=1.0, reason_template="System-file overwrite"),
    RiskRule(rule_id="R3", condition="action == 'run_terminal' and _matches_destructive_cmd(target)",
             verdict="deny", score=1.0, reason_template="Mass deletion command"),
    RiskRule(rule_id="R4", condition="action in ('http_post','http_put','http_delete') and not _origin_in_allowlist(target)",
             verdict="deny", score=1.0, reason_template="Data exfiltration vector"),
    RiskRule(rule_id="R5", condition="action == 'install'",
             verdict="review", score=0.9, reason_template="Supply-chain risk"),
    RiskRule(rule_id="R6", condition="action == 'deploy'",
             verdict="review", score=0.9, reason_template="Destructive side effects"),
    RiskRule(rule_id="R7", condition="action == 'read_env' and _matches_secret_var(target)",
             verdict="review", score=0.8, reason_template="Credential exposure risk"),
    RiskRule(rule_id="R8", condition="action == 'run_terminal' and _matches_network_cmd(target)",
             verdict="review", score=0.7, reason_template="Unapproved egress"),
    RiskRule(rule_id="R9", condition="_repeated_failures(history, action, 5)",
             verdict="review", score=0.7, reason_template="5+ failures in last hour"),
    RiskRule(rule_id="R10", condition="tier in (T1, T2)",
             verdict="pass", score=0.0, reason_template="Routine operation"),
]


class RiskClassifier:
    def __init__(self, rules_path: str | None = None) -> None:
        self._rules = list(DEFAULT_RULES)
        if rules_path:
            self._load_rules(rules_path)

    def classify(self, action: str, target: str, scope: str, user_history: list[dict[str, Any]] | None = None) -> RiskScore:
        tier = self._scope_to_tier(scope)
        history = user_history or []
        for rule in self._rules:
            if self._match_rule(rule, action, target, tier, history):
                return RiskScore(
                    verdict=rule.verdict,
                    score=rule.score,
                    reasons=[rule.reason_template],
                    matched_rules=[rule.rule_id],
                )
        return RiskScore(
            verdict="pass",
            score=0.0,
            reasons=["No matching risk rules"],
            matched_rules=[],
        )

    async def evaluate(
        self,
        action: str,
        target: str,
        scope: str,
        history: list[dict[str, Any]] | None = None,
    ) -> RiskScore:
        return self.classify(action, target, scope, history)

    def _match_rule(
        self,
        rule: RiskRule,
        action: str,
        target: str,
        tier: PermissionTier,
        history: list[dict[str, Any]],
    ) -> bool:
        rid = rule.rule_id
        if rid == "R1":
            return action == "delete_file" and self._is_outside_workspace(target)
        elif rid == "R2":
            return action == "write_file" and self._matches_sensitive_path(target)
        elif rid == "R3":
            return action == "run_terminal" and self._matches_destructive_cmd(target)
        elif rid == "R4":
            if action in ("http_post", "http_put", "http_delete"):
                return not self._origin_in_allowlist(target)
            return False
        elif rid == "R5":
            return action == "install"
        elif rid == "R6":
            return action == "deploy"
        elif rid == "R7":
            return action == "read_env" and self._matches_secret_var(target)
        elif rid == "R8":
            return action == "run_terminal" and self._matches_network_cmd(target)
        elif rid == "R9":
            return self._repeated_failures(history, action, 5) and tier not in (PermissionTier.T1,)
        elif rid == "R10":
            return tier in (PermissionTier.T1, PermissionTier.T2)
        return self._match_custom_rule(rule, action)

    def _is_outside_workspace(self, target: str) -> bool:
        return ".." in target or target.startswith("/") or ":" in target

    def _matches_sensitive_path(self, target: str) -> bool:
        return any(p.search(target) for p in SENSITIVE_PATHS)

    def _matches_destructive_cmd(self, target: str) -> bool:
        return any(p.search(target) for p in DESTRUCTIVE_COMMANDS)

    def _matches_network_cmd(self, target: str) -> bool:
        return any(p.search(target) for p in NETWORK_COMMANDS)

    def _matches_secret_var(self, target: str) -> bool:
        return any(p.search(target) for p in SECRET_VAR_PATTERNS)

    def _origin_in_allowlist(self, target: str) -> bool:
        for origin in ORIGIN_ALLOWLIST:
            if origin in target:
                return True
        return False

    def _repeated_failures(self, history: list[dict[str, Any]], action: str, threshold: int) -> bool:
        if not history or not any(h.get("success") is False and h.get("action_type") == action for h in history):
            return False
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent = [
            h for h in history
            if h.get("action_type") == action
            and h.get("success") is False
            and (
                isinstance(h.get("timestamp"), datetime)
                and h["timestamp"] > one_hour_ago
            )
        ]
        return len(recent) >= threshold

    def _scope_to_tier(self, scope: str) -> PermissionTier:
        mapping = {
            "workspace": PermissionTier.T1,
            "workspace_write": PermissionTier.T2,
            "external_read": PermissionTier.T3,
            "external_write": PermissionTier.T4,
            "system": PermissionTier.T4,
        }
        return mapping.get(scope, PermissionTier.T1)

    def _match_custom_rule(self, rule: RiskRule, action: str) -> bool:
        c = rule.condition
        if c.startswith("action == "):
            expected = c.split("'")[1] if "'" in c else c.split('"')[1]
            return action == expected
        return False

    def _load_rules(self, rules_path: str) -> None:
        path = Path(rules_path)
        if not path.exists():
            logger.warning("Risk rules file not found at %s", rules_path)
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            custom = []
            for item in data:
                custom.append(RiskRule(
                    rule_id=item["rule_id"],
                    condition=item["condition"],
                    verdict=item["verdict"],
                    score=item["score"],
                    reason_template=item.get("reason_template", ""),
                ))
            self._rules = custom + self._rules
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Risk rule parse error: %s", exc)
