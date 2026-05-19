from schemas.intent import IntentExtraction
from utils.retry import parse_with_retry
from .client import AIClient

SYSTEM_PROMPT = """You are an intent extraction engine for Vunoh, a diaspora financial operations platform.
Your output must be valid JSON only — no markdown, no explanation, no extra fields.

Allowed intents: send_money | verify_document | hire_service | airport_transfer | general_inquiry
Urgency levels: low | medium | high

Extract these fields only:
{
  "intent": "<allowed_intent>",
  "confidence": <0.0-1.0>,
  "entities": { <relevant key/value pairs from the request> },
  "urgency_level": "<low|medium|high>",
  "risk_flags": [<list of string flags if any>]
}

Entity extraction rules:
- amount: numeric value if mentioned (number only, no currency symbol)
- recipient: who the money/service is for
- location: city or country if mentioned
- document_type: passport, title, certificate, etc. if mentioned
- returning_customer: true only if explicitly stated

Never add fields outside the schema above. Never wrap in markdown code blocks."""


class IntentExtractor:
    def __init__(self):
        self.client = AIClient()

    def extract(self, customer_request: str) -> IntentExtraction:
        return parse_with_retry(
            call_fn=lambda: self.client.complete(SYSTEM_PROMPT, customer_request, temperature=0.1),
            schema=IntentExtraction,
        )
