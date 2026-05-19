from decouple import config

from .base import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=config("GEMINI_API_KEY"))
        return self._client

    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        from google.genai import types
        prompt = f"{system}\n\n{user}"
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=temperature,
            ),
        )
        return response.text
