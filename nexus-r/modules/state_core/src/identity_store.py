from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet


class IdentityStore:
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

    def read(self) -> dict[str, object]:
        if not self.data_path.exists():
            return {}
        payload = self._fernet.decrypt(self.data_path.read_bytes())
        import json

        return json.loads(payload.decode("utf-8"))

    def write(self, data: dict[str, object]) -> None:
        import json

        token = self._fernet.encrypt(json.dumps(data).encode("utf-8"))
        self.data_path.write_bytes(token)
