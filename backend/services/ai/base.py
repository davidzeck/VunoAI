from abc import ABC, abstractmethod


class RateLimitError(Exception):
    """Raised by a provider when it hits its rate or quota limit."""


class AllProvidersExhaustedError(Exception):
    """Raised when all AI providers are rate-limited or unavailable."""


class AIProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        ...
