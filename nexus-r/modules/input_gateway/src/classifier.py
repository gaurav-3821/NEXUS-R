from __future__ import annotations

import re


class TaskClassifier:
    _PATTERNS: list[tuple[str, tuple[str, ...]]] = [
        ("append_file", ("append", "add to file")),
        ("write_file", ("create file", "write file", "make file", "save file")),
        ("read_file", ("read file", "show file", "open file", "display file")),
        ("search_text", ("find", "search", "grep", "contains")),
        ("list_files", ("list files", "show files", "list all", "show all", "files in")),
        ("run_terminal", ("run command", "execute command", "terminal", "shell")),
        ("general_llm", ("hello", "hi", "summarize", "draft", "brainstorm", "explain")),
    ]

    def classify(self, text: str) -> tuple[str, float, float]:
        normalized = text.strip().lower()
        if not normalized:
            return "unknown", 0.0, 0.0

        if any(word in normalized for word in ("deploy", "production", "rotate", "secret", "credential")):
            return "unknown", self._complexity(normalized, "unknown"), 0.2

        if re.search(r"\b(list|show)\b.+\b(py|python)\b.+\bfiles?\b", normalized):
            return "list_files", self._complexity(normalized, "list_files"), 0.85
        if re.search(r"\b(create|write)\b.+\bfile\b", normalized):
            return "write_file", self._complexity(normalized, "write_file"), 0.8
        if re.search(r"\b(create|write|make)\b\s+[a-zA-Z0-9_.\\/-]+\.[a-zA-Z0-9]+\b", normalized):
            return "write_file", self._complexity(normalized, "write_file"), 0.82
        if re.search(r"\b(append|add)\b.+\b[a-zA-Z0-9_.\\/-]+\.[a-zA-Z0-9]+\b", normalized):
            return "append_file", self._complexity(normalized, "append_file"), 0.8
        if re.search(r"\b(read|open|show)\b.+\b[a-z0-9_.\\/-]+\b", normalized):
            return "read_file", self._complexity(normalized, "read_file"), 0.7
        if re.search(r"`[^`]+`", text):
            return "run_terminal", self._complexity(normalized, "run_terminal"), 0.75
        for task_type, markers in self._PATTERNS:
            if task_type == "general_llm":
                continue
            if any(re.search(rf"\b{re.escape(marker)}\b", normalized) for marker in markers):
                return task_type, self._complexity(normalized, task_type), 0.9
        if any(
            re.search(rf"\b{re.escape(marker)}\b", normalized)
            for marker in ("hello", "hi", "summarize", "draft", "brainstorm", "explain")
        ):
            return "general_llm", self._complexity(normalized, "general_llm"), 0.9
        return "unknown", self._complexity(normalized, "unknown"), 0.3

    def _complexity(self, text: str, task_type: str) -> float:
        score = 0.2
        tokens = len(text.split())
        score += min(tokens / 40.0, 0.3)
        if any(word in text for word in ("and then", "also", "after that")):
            score += 0.2
        if task_type in {"write_file", "append_file", "run_terminal"}:
            score += 0.15
        if any(word in text for word in ("analyze", "summarize", "refactor", "explain")):
            score += 0.25
        return min(score, 1.0)
