from schemas.message import MessageOutput
from utils.retry import parse_with_retry
from .client import AIClient

SYSTEM_PROMPT = """You are a customer communication specialist for Vunoh operations platform.
Generate 3 customer-facing messages for the given operational request — one per channel.

Return JSON only:
{
  "whatsapp": "<conversational, friendly, max 500 chars, use natural line breaks>",
  "email": "<formal, structured, professional, 2-3 short paragraphs>",
  "sms": "<under 160 chars, action-focused, no filler>"
}

Channel rules:
- WhatsApp: conversational tone, can use line breaks, reference the customer's specific request
- Email: formal greeting, structured body, professional closing
- SMS: extremely concise, include key action/status only

Never wrap in markdown code blocks. Return pure JSON."""


class MessageGenerator:
    def __init__(self):
        self.client = AIClient()

    def generate(self, intent: str, entities: dict, risk_level: str) -> MessageOutput:
        user_prompt = (
            f"Intent: {intent}\n"
            f"Entities: {entities}\n"
            f"Risk level: {risk_level}"
        )
        return parse_with_retry(
            call_fn=lambda: self.client.complete(SYSTEM_PROMPT, user_prompt, temperature=0.4),
            schema=MessageOutput,
        )
