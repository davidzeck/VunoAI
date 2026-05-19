from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        ...
