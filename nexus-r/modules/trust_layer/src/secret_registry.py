from __future__ import annotations

import os


try:
    import keyring  # type: ignore
except ImportError:  # pragma: no cover
    keyring = None


class SecretRegistry:
    def __init__(self, app_name: str = "nexus-r") -> None:
        self.app_name = app_name
        self._memory_store: dict[str, str] = {}

    def set_secret(self, name: str, value: str) -> None:
        if keyring is not None:
            try:
                keyring.set_password(self.app_name, name, value)
                return
            except Exception:
                pass
        self._memory_store[name] = value

    def get_secret(self, name: str) -> str | None:
        if keyring is not None:
            try:
                secret = keyring.get_password(self.app_name, name)
            except Exception:
                secret = None
            if secret is not None:
                return secret
        if name in self._memory_store:
            return self._memory_store[name]
        return None

    def bootstrap_from_environment(self, secret_name: str, environment_variable: str) -> bool:
        value = os.environ.get(environment_variable)
        if not value:
            return False
        self._memory_store.setdefault(secret_name, value)
        return True

    def delete_secret(self, name: str) -> None:
        if keyring is not None:
            try:
                keyring.delete_password(self.app_name, name)
            except Exception:
                pass
        self._memory_store.pop(name, None)
