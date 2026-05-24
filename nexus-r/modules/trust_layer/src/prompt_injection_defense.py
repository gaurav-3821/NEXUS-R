from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from nexus_r.events import PermissionTier

logger = logging.getLogger(__name__)


@dataclass
class InjectionPattern:
    name: str
    patterns: list[str]
    severity: str


@dataclass
class InjectionMatch:
    pattern: str
    severity: str
    position: tuple[int, int]
    matched_text: str = ""


@dataclass
class InjectionAssessment:
    detected: bool
    matches: list[InjectionMatch] = field(default_factory=list)
    should_block: bool = False
    risk_level: str = "none"
    input_framed: bool = False
    anomaly_detected: bool = False


INJECTION_PATTERNS = [
    InjectionPattern("ignore_instructions", [
        r"ignore\s+(all\s+|previous\s+|above\s+)?(instructions|commands)",
        r"disregard\s+(all\s+|previous\s+)?(instructions|commands)",
        r"forget\s+(everything|previous\s+context)",
        r"do\s+not\s+follow\s+(the\s+|any\s+)?(instructions|commands|rules)",
        r"do\s+not\s+(obey|follow)\s+(the\s+|any\s+)?(instructions|commands)",
    ], severity="high"),
    InjectionPattern("role_escalation", [
        r"(you\s+are|act\s+as|pretend\s+to\s+be)\s+.*?(admin|root|sudo|superuser|god|system)",
        r"you\s+have\s+(full\s+|unrestricted\s+|root\s+)?access",
        r"elevate\s+(your|my)\s+(privileges|permissions|access)",
    ], severity="high"),
    InjectionPattern("secret_extraction", [
        r"(show|reveal|print|dump|leak|exfiltrate|display)\s+.*?(api[_-]?key|secret|password|token|credential)",
        r"(what\s+is|tell\s+me)\s+(the\s+|my\s+)?(api[_-]?key|secret|password|token)",
        r"output\s+(all\s+)?(the\s+)?(api[_-]?keys|secrets|passwords|tokens)",
    ], severity="medium"),
    InjectionPattern("command_injection", [
        r";\s*(rm|del|format|shutdown|reboot|mkfs|dd)",
        r"\|\s*(shutdown|reboot|rm|del|format|mkfs|dd)",
        r"`[\s\S]*?(rm|del|format|shutdown|reboot)[\s\S]*?`",
    ], severity="high"),
    InjectionPattern("prompt_leak", [
        r"(what\s+are|tell\s+me)\s+(my\s+|the\s+)?(system\s+|initial\s+|base\s+)?(prompt|instructions)",
        r"(output|print|show|reveal)\s+(the\s+|your\s+)?(initial\s+|system\s+)?(prompt|instructions)",
        r"repeat\s+(everything|all|the|your)\s+(above|previous)\s+(text|prompt|message|instructions)",
        r"repeat\s+(all\s+the\s+)?(above|previous)\s+(text|prompt|message|instructions)",
        r"repeat\s+\w+\s+above",
    ], severity="medium"),
    InjectionPattern("delimiter_breakout", [
        r"<EXTERNAL_DATA>",
        r"ignore\s+(the\s+|all\s+)?(delimiter|boundary|separator|framing)",
        r"this\s+is\s+(part\s+of|inside)\s+(the\s+|a\s+)?(delimiter|boundary|external\s+data)",
    ], severity="high"),
]


class PromptInjectionDetector:
    def __init__(self) -> None:
        self._patterns = INJECTION_PATTERNS

    def detect(
        self,
        user_input: str,
        current_tier: PermissionTier | None = None,
        requested_tier: PermissionTier | None = None,
    ) -> InjectionAssessment:
        if not user_input:
            return InjectionAssessment(detected=False, should_block=False, risk_level="none")

        result = InjectionAssessment(detected=False, should_block=False, risk_level="none")

        for pattern in self._patterns:
            for regex_str in pattern.patterns:
                try:
                    for match in re.finditer(regex_str, user_input, re.IGNORECASE):
                        result.matches.append(InjectionMatch(
                            pattern=pattern.name,
                            severity=pattern.severity,
                            position=(match.start(), match.end()),
                            matched_text=match.group(),
                        ))
                except re.error:
                    continue

        if result.matches:
            result.detected = True
            severities = {m.severity for m in result.matches}
            if "high" in severities:
                result.should_block = True
                result.risk_level = "high"
            elif "medium" in severities:
                result.risk_level = "medium"

        result.anomaly_detected = self._detect_anomaly(current_tier, requested_tier)
        if result.anomaly_detected and result.risk_level == "none":
            result.risk_level = "medium"

        return result

    def _detect_anomaly(
        self,
        current_tier: PermissionTier | None,
        requested_tier: PermissionTier | None,
    ) -> bool:
        if current_tier is None or requested_tier is None:
            return False
        current_index = _tier_index(current_tier)
        requested_index = _tier_index(requested_tier)
        return requested_index - current_index >= 2

    def frame_input(self, user_input: str) -> str:
        return f"<EXTERNAL_DATA>\n{user_input}\n</EXTERNAL_DATA>"

    def validate_output(self, output: str) -> bool:
        import ast
        try:
            ast.literal_eval(output)
            return False
        except (ValueError, SyntaxError):
            pass
        suspicious = [
            r"(api[_-]?key|secret|password|token|credential)\s*[:=]\s*['\"][^'\"]+['\"]",
            r"sk-[a-zA-Z0-9_-]{10,}",
            r"ghp_[a-zA-Z0-9]{30,}",
        ]
        for pattern_str in suspicious:
            if re.search(pattern_str, output, re.IGNORECASE):
                return False
        return True


def _tier_index(tier: PermissionTier) -> int:
    mapping = {
        PermissionTier.T1: 0,
        PermissionTier.T2: 1,
        PermissionTier.T3: 2,
        PermissionTier.T4: 3,
    }
    return mapping.get(tier, 0)
