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
- recipient: who the money/service is for (name or description)
- location: city or country if mentioned
- document_type: general document category (passport, title, certificate, etc.)
- document_subtype: specific type — one of: "land_title", "title_deed", "passport",
  "national_id", "kyc", "birth_certificate", "marriage_certificate",
  "academic_certificate", "business_permit", or "other".
  Extract only when intent is verify_document.
- destination_country: the country money is being sent TO if cross-border is mentioned
  (e.g. "send to UK", "transfer to Germany"). Leave absent for domestic Kenya transfers.
- is_new_recipient: true if customer implies this is a first-time transfer to this person
  or they do not know the recipient well. false if they reference an existing contact.
  Omit entirely if unclear — do not guess.
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
