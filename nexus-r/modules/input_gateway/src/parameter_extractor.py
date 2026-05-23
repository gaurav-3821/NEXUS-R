from __future__ import annotations

import re


class ParameterExtractor:
    def extract(self, text: str, task_type: str) -> dict[str, str]:
        extractor = getattr(self, f"_extract_{task_type}", self._extract_unknown)
        return extractor(text)

    def _extract_list_files(self, text: str) -> dict[str, str]:
        params = {"path": self._extract_location(text) or ".", "pattern": "*"}
        if "python file" in text.lower() or ".py" in text.lower():
            params["pattern"] = "*.py"
        return params

    def _extract_read_file(self, text: str) -> dict[str, str]:
        return {"path": self._extract_file_path(text) or ""}

    def _extract_write_file(self, text: str) -> dict[str, str]:
        return {
            "path": self._extract_file_path(text) or "untitled.txt",
            "content": self._extract_content(text),
        }

    def _extract_append_file(self, text: str) -> dict[str, str]:
        return {
            "path": self._extract_file_path(text) or "untitled.txt",
            "content": self._extract_content(text),
        }

    def _extract_search_text(self, text: str) -> dict[str, str]:
        match = re.search(r'["\']([^"\']+)["\']', text)
        return {
            "query": match.group(1) if match else "",
            "path": self._extract_location(text) or ".",
            "pattern": "*.txt" if ".txt" in text.lower() else "*",
        }

    def _extract_run_terminal(self, text: str) -> dict[str, str]:
        backtick = re.search(r"`([^`]+)`", text)
        if backtick:
            return {"command": backtick.group(1)}
        lowered = text.lower()
        for marker in ("run command", "execute command", "terminal", "shell"):
            if marker in lowered:
                index = lowered.index(marker) + len(marker)
                return {"command": text[index:].strip(" :")}
        return {"command": ""}

    def _extract_unknown(self, text: str) -> dict[str, str]:
        return {"raw": text}

    def _extract_general_llm(self, text: str) -> dict[str, str]:
        return {"prompt": text}

    def _extract_file_path(self, text: str) -> str | None:
        quoted = re.search(r'["\']([^"\']+\.[a-z0-9]+)["\']', text, re.IGNORECASE)
        if quoted:
            return quoted.group(1)
        bare = re.search(r"\b([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)\b", text)
        if bare:
            return bare.group(1)
        return None

    def _extract_location(self, text: str) -> str | None:
        quoted = re.search(r'\bin\s+["\']([^"\']+)["\']', text, re.IGNORECASE)
        if quoted:
            return quoted.group(1)
        bare = re.search(r"\bin\s+([a-zA-Z0-9_./\\-]+)", text, re.IGNORECASE)
        if bare:
            return bare.group(1)
        return None

    def _extract_content(self, text: str) -> str:
        for marker in ("with content", "containing", "with", "saying"):
            pattern = re.compile(rf"{marker}\s+(.+)$", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return match.group(1).strip().strip('"').strip("'")
        return ""
