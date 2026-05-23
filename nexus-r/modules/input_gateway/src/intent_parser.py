from __future__ import annotations

from nexus_r.events import IntentResult, PermissionTier

from .classifier import TaskClassifier
from .parameter_extractor import ParameterExtractor


class IntentParser:
    def __init__(
        self,
        classifier: TaskClassifier | None = None,
        extractor: ParameterExtractor | None = None,
    ) -> None:
        self.classifier = classifier or TaskClassifier()
        self.extractor = extractor or ParameterExtractor()

    def parse(self, user_input: str) -> IntentResult:
        raw = user_input or ""
        normalized = " ".join(raw.split())
        task_type, complexity, confidence = self.classifier.classify(normalized)
        parameters = self.extractor.extract(normalized, task_type)
        warnings: list[str] = []
        if task_type == "unknown":
            warnings.append("Task could not be mapped to a Phase 1 action.")
        if not normalized:
            warnings.append("Empty input received.")
        return IntentResult(
            raw_input=raw,
            normalized_input=normalized,
            task_type=task_type,
            complexity=complexity,
            confidence=confidence,
            parameters=parameters,
            suggested_tier=self._suggest_tier(task_type),
            warnings=warnings,
        )

    def _suggest_tier(self, task_type: str) -> PermissionTier:
        if task_type in {"write_file", "append_file", "run_terminal"}:
            return PermissionTier.T2
        return PermissionTier.T1
