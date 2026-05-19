from pydantic import BaseModel

from .client import AIClient
from utils.retry import parse_with_retry


class ScopeCheck(BaseModel):
    in_scope: bool
    reason: str


SYSTEM = """
You are a strict scope classifier for Vunoh, a diaspora financial operations platform.

Vunoh handles ONLY these five operational request types:
  1. send_money         — wire transfers, M-Pesa sends, remittances to Kenya/Africa
  2. verify_document    — title deeds, passports, ID cards, KYC document checks
  3. hire_service       — hiring tradespeople or domestic workers (plumbers, electricians, cleaners, drivers)
  4. airport_transfer   — vehicle pickup/dropoff at airports, travel logistics
  5. general_inquiry    — questions SPECIFICALLY about: account balance, transaction status, exchange rates, Vunoh fees, Vunoh platform features

Return JSON only — no markdown, no explanation:
{ "in_scope": true/false, "reason": "<one concise sentence>" }

Rules:
- general_inquiry is ONLY for Vunoh-specific account and platform questions. It does NOT cover creative writing, general knowledge, cooking, travel advice, or anything unrelated to Vunoh's services.
- If the request is about writing, storytelling, general information, entertainment, or anything outside the 5 categories above, set in_scope to false.
- Be strict. When in doubt, set in_scope to false.

Examples of OUT-OF-SCOPE requests (in_scope = false):
  - "Write me a poem about Nairobi"
  - "What is the capital of Kenya?"
  - "Tell me a joke"
  - "Book me a flight to London"
  - "What restaurants are in Westlands?"
"""


class ScopeChecker:
    def __init__(self):
        self.client = AIClient()

    def check(self, customer_request: str) -> ScopeCheck:
        return parse_with_retry(
            lambda: self.client.complete(SYSTEM, customer_request, temperature=0.0),
            ScopeCheck,
        )
