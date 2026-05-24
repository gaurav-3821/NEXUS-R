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


class ProviderError(NexusError):
    """Base for all provider invocation errors."""

    def __init__(self, message: str, *, provider: str, tier: str, failure_class: str, retryable: bool, fallback_decision: str):
        self.provider = provider
        self.tier = tier
        self.failure_class = failure_class
        self.retryable = retryable
        self.fallback_decision = fallback_decision
        super().__init__(message)

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "tier": self.tier,
            "failure_class": self.failure_class,
            "retryable": self.retryable,
            "fallback_decision": self.fallback_decision,
            "message": str(self),
        }


class ProviderConnectionError(ProviderError):
    """Provider is unreachable."""


class ProviderTimeoutError(ProviderError):
    """Provider did not respond within the timeout window."""


class ProviderAuthError(ProviderError):
    """Provider rejected credentials."""


class ProviderRateLimitError(ProviderError):
    """Provider returned a rate-limit response."""


class ProviderModelUnavailableError(ProviderError):
    """Provider does not have the requested model deployed."""


class ProviderMalformedResponseError(ProviderError):
    """Provider returned an unparseable or incomplete response."""


class ProviderEmptyResponseError(ProviderError):
    """Provider returned a response with no usable content."""
