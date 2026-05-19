from decouple import config
from groq import Groq

from .base import AIProvider


class GroqProvider(AIProvider):
    def __init__(self):
        self._client = None
        self.model   = "llama-3.3-70b-versatile"

    @property
    def client(self):
        if self._client is None:
            self._client = Groq(api_key=config("GROQ_API_KEY"))
        return self._client

    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content
