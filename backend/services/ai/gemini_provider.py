import google.generativeai as genai
from decouple import config

from .base import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self):
        genai.configure(api_key=config("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"},
        )

    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        prompt   = f"{system}\n\n{user}"
        response = self.model.generate_content(prompt)
        return response.text
