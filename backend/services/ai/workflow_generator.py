from schemas.workflow import WorkflowOutput
from utils.retry import parse_with_retry
from .client import AIClient

SYSTEM_PROMPT = """You are an operational workflow generator for Vunoh operations platform.
Generate 4-7 concise operational fulfillment steps for the given customer request.

Return JSON only:
{ "steps": ["Step description...", "Step description...", ...] }

Rules:
- Steps must be imperative and operational (e.g. "Verify sender KYC", "Confirm recipient details")
- No greetings, no filler, no customer-facing language
- Steps should reflect real internal operations
- Between 4 and 7 steps only
- Never wrap in markdown code blocks"""


class WorkflowGenerator:
    def __init__(self):
        self.client = AIClient()

    def generate(self, intent: str, entities: dict) -> WorkflowOutput:
        user_prompt = f"Intent: {intent}\nEntities: {entities}"
        return parse_with_retry(
            call_fn=lambda: self.client.complete(SYSTEM_PROMPT, user_prompt, temperature=0.1),
            schema=WorkflowOutput,
        )
