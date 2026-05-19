from dataclasses import dataclass
from typing import Callable


@dataclass
class RiskRule:
    condition:   Callable[[dict], bool]
    score:       int
    flag:        str
    explanation: str


RULES: list[RiskRule] = [
    RiskRule(
        condition=lambda e: float(e.get("amount", 0)) > 100_000,
        score=25, flag="high_amount",
        explanation="Large transfer amount detected",
    ),
    RiskRule(
        condition=lambda e: e.get("urgency_level") == "high",
        score=10, flag="urgent_request",
        explanation="Urgency increases fraud risk",
    ),
    RiskRule(
        condition=lambda e: e.get("intent") == "verify_document",
        score=35, flag="document_verification",
        explanation="Document verification is a high-risk operation",
    ),
    RiskRule(
        condition=lambda e: "unknown" in str(e.get("recipient", "")).lower(),
        score=20, flag="unknown_recipient",
        explanation="Recipient identity is unverified",
    ),
    RiskRule(
        condition=lambda e: float(e.get("amount", 0)) > 500_000,
        score=20, flag="very_high_amount",
        explanation="Very large transfer — escalation required",
    ),
    RiskRule(
        condition=lambda e: e.get("returning_customer") is True,
        score=-15, flag="trusted_customer",
        explanation="Returning customer — reduced risk",
    ),
]

_RISK_LEVELS = [
    (0,  30,  "low"),
    (31, 70,  "medium"),
    (71, 100, "high"),
]


def calculate_risk(intent_data: dict) -> dict:
    merged = {**intent_data, **intent_data.get("entities", {})}

    score        = 0
    flags        = []
    explanations = []

    for rule in RULES:
        try:
            if rule.condition(merged):
                score += rule.score
                flags.append(rule.flag)
                explanations.append(rule.explanation)
        except Exception:
            continue

    score = max(0, min(100, score))
    level = next(lv for lo, hi, lv in _RISK_LEVELS if lo <= score <= hi)

    return {
        "risk_score":          score,
        "risk_level":          level,
        "risk_flags":          flags,
        "risk_explanation":    explanations,
        "escalation_required": score >= 71,
    }
