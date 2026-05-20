import time

import structlog

from .base import AllProvidersExhaustedError, RateLimitError
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider

log = structlog.get_logger()

COOLDOWN_SECONDS = 60  # how long to skip a rate-limited provider


class AIClient:
    def __init__(self):
        self._providers = {
            "groq":   GroqProvider(),
            "gemini": GeminiProvider(),
        }
        self._rate_limited_until: dict[str, float] = {}

    def _is_cooling(self, name: str) -> bool:
        return time.time() < self._rate_limited_until.get(name, 0)

    def _mark_limited(self, name: str) -> None:
        self._rate_limited_until[name] = time.time() + COOLDOWN_SECONDS
        log.warning("provider_rate_limited", provider=name, cooldown_seconds=COOLDOWN_SECONDS)

    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        # groq appears twice: first attempt, then again after gemini if cooldown expired
        order = ["groq", "gemini", "groq"]
        last_error: Exception | None = None

        for name in order:
            if self._is_cooling(name):
                log.info("provider_skipped_cooling", provider=name)
                continue

            try:
                result = self._providers[name].complete(system, user, temperature)
                log.info("provider_success", provider=name)
                return result

            except RateLimitError as exc:
                self._mark_limited(name)
                last_error = exc

            except Exception as exc:
                # Non-rate-limit error: fall through to next provider but no cooldown
                log.warning("provider_error_falling_back", provider=name, error=str(exc))
                last_error = exc

        raise AllProvidersExhaustedError(
            f"rate_limit_exceeded: all AI providers are at capacity. Last error: {last_error}"
        )
