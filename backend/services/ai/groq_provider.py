from decouple import config
from groq import Groq

from .base import AIProvider


class GroqProvider(AIProvider):
    def __init__(self):
        self.client = Groq(api_key=config("GROQ_API_KEY"))
        self.model  = "llama-3.3-70b-versatile"

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
