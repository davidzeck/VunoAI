import structlog

from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider

log = structlog.get_logger()


class AIClient:
    def __init__(self):
        self.primary  = GroqProvider()
        self.fallback = GeminiProvider()

    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        try:
            return self.primary.complete(system, user, temperature)
        except Exception as exc:
            log.warning("groq_failed_falling_back", error=str(exc))
            return self.fallback.complete(system, user, temperature)
