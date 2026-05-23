class NexusError(Exception):
    """Base error for NEXUS-R."""


class ConfigurationError(NexusError):
    """Raised when the runtime configuration is invalid."""


class IntentParseError(NexusError):
    """Raised when user input cannot be safely parsed."""


class PermissionDeniedError(NexusError):
    """Raised when an action exceeds the allowed permission tier."""


class SandboxExecutionError(NexusError):
    """Raised when sandbox execution fails."""


class StateStoreError(NexusError):
    """Raised when state persistence fails."""


class SessionStateError(NexusError):
    """Raised when session persistence or recovery fails."""


class SessionPathMismatchError(SessionStateError):
    """Raised when a session is resumed from a different canonical workspace."""
