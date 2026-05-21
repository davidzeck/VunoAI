from dataclasses import dataclass, field
from typing import Callable

import structlog

log = structlog.get_logger()

_FATF_COUNTRIES = {
    "united kingdom", "uk", "great britain",
    "united states", "us", "usa",
    "germany", "deutschland",
    "canada",
    "france",
    "united arab emirates", "uae", "dubai",
    "australia",
    "netherlands",
    "switzerland",
}

_LAND_TITLE_SUBTYPES = {"land_title", "title_deed", "land"}
_IDENTITY_SUBTYPES   = {"passport", "national_id", "kyc"}


@dataclass
class RiskRule:
    condition:       Callable[[dict], bool]
    score:           int
    flag:            str
    explanation:     str
    weight_category: str = "general"


def _amount(e: dict) -> float:
    try:
        return float(e.get("amount", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _is_domestic(e: dict) -> bool:
    """True when no destination_country or destination is explicitly Kenya."""
    dc = str(e.get("destination_country", "") or "").strip().lower()
    return dc == "" or dc == "kenya"


RULES: list[RiskRule] = [

    # ── INTENT BASELINES ───────────────────────────────────────────────────────
    # R01: general inquiry pulls score toward zero — no funds at risk
    RiskRule(
        condition=lambda e: e.get("intent") == "general_inquiry",
        score=-20, flag="no_financial_transaction",
        explanation="Balance/rate inquiry — no funds at risk",
        weight_category="intent",
    ),
    # R02: airport transfer is logistics only
    RiskRule(
        condition=lambda e: e.get("intent") == "airport_transfer",
        score=-10, flag="logistics_only",
        explanation="Logistics operation — no direct financial transfer",
        weight_category="intent",
    ),
    # R03: any financial transfer carries base risk
    RiskRule(
        condition=lambda e: e.get("intent") == "send_money",
        score=5, flag="financial_transaction",
        explanation="Financial transfer — base risk applies",
        weight_category="intent",
    ),
    # R04: service payment carries minor financial exposure
    RiskRule(
        condition=lambda e: e.get("intent") == "hire_service",
        score=5, flag="service_transaction",
        explanation="Service payment — minor financial exposure",
        weight_category="intent",
    ),

    # ── AMOUNT TIERS ───────────────────────────────────────────────────────────
    # R05: large transfer (>KES 100k)
    RiskRule(
        condition=lambda e: _amount(e) > 100_000,
        score=25, flag="high_amount",
        explanation="Transfer exceeds KES 100,000 — elevated monitoring required",
        weight_category="amount",
    ),
    # R06: very large transfer (>KES 500k) — AML reporting threshold
    RiskRule(
        condition=lambda e: _amount(e) > 500_000,
        score=20, flag="very_high_amount",
        explanation="Very large transfer — AML reporting threshold exceeded",
        weight_category="amount",
    ),
    # R07: exceeds M-Pesa single-transaction ceiling (KES 150k) for domestic transfers
    #      M-Pesa can't process >150k in one transaction — expectation of this is suspicious
    RiskRule(
        condition=lambda e: _amount(e) > 150_000 and _is_domestic(e),
        score=30, flag="mpesa_ceiling_breach",
        explanation="Exceeds M-Pesa single-transaction limit (KES 150,000) — operationally suspicious for domestic transfer",
        weight_category="amount",
    ),
    # R08: round amount (multiples of 50k ≥ 50k) — pre-negotiated fraud indicator
    RiskRule(
        condition=lambda e: _amount(e) >= 50_000 and _amount(e) % 50_000 < 0.01,
        score=10, flag="round_amount_signal",
        explanation="Round amount is a common pre-negotiated fraud indicator",
        weight_category="amount",
    ),

    # ── URGENCY ────────────────────────────────────────────────────────────────
    # R09: urgency is the #1 social engineering vector in diaspora fraud
    RiskRule(
        condition=lambda e: e.get("urgency_level") == "high",
        score=20, flag="urgent_request",
        explanation="High urgency is the primary social engineering signal in diaspora fraud",
        weight_category="urgency",
    ),
    # R10: urgency + new recipient — the canonical Kenya diaspora fraud pattern
    #      ("send NOW, my mother is in hospital, to someone you've never sent to")
    RiskRule(
        condition=lambda e: (
            e.get("urgency_level") == "high" and
            e.get("is_new_recipient") is True
        ),
        score=15, flag="urgent_new_recipient_combo",
        explanation="Urgent transfer to a first-time recipient — the #1 diaspora fraud script",
        weight_category="urgency",
    ),

    # ── RECIPIENT ──────────────────────────────────────────────────────────────
    # R11: first-time recipient (replaces the old fragile "unknown" string match)
    RiskRule(
        condition=lambda e: e.get("is_new_recipient") is True,
        score=20, flag="new_recipient",
        explanation="First-time recipient — identity unverified, elevated fraud risk",
        weight_category="recipient",
    ),
    # R12: no recipient named at all for a money transfer
    RiskRule(
        condition=lambda e: (
            e.get("intent") == "send_money" and
            not str(e.get("recipient", "") or "").strip()
        ),
        score=15, flag="missing_recipient",
        explanation="No recipient named for a money transfer — cannot verify destination",
        weight_category="recipient",
    ),

    # ── DOCUMENT TYPE ──────────────────────────────────────────────────────────
    # R13: document verification base risk
    RiskRule(
        condition=lambda e: e.get("intent") == "verify_document",
        score=15, flag="document_verification",
        explanation="Document verification carries baseline fraud and forgery risk",
        weight_category="document",
    ),
    # R14: Kenya land title — the highest-risk document category nationally
    RiskRule(
        condition=lambda e: str(e.get("document_subtype", "") or "").lower() in _LAND_TITLE_SUBTYPES,
        score=30, flag="land_title_fraud_risk",
        explanation="Kenya land title fraud is the highest-risk document category — manual verification mandatory",
        weight_category="document",
    ),
    # R15: identity documents — standard KYC risk
    RiskRule(
        condition=lambda e: str(e.get("document_subtype", "") or "").lower() in _IDENTITY_SUBTYPES,
        score=10, flag="identity_document",
        explanation="Identity document verification — standard KYC elevated risk",
        weight_category="document",
    ),

    # ── GEOGRAPHY ──────────────────────────────────────────────────────────────
    # R16: cross-border transfer (destination outside Kenya)
    RiskRule(
        condition=lambda e: (
            bool(e.get("destination_country")) and
            str(e.get("destination_country", "")).strip().lower() not in {"", "kenya"}
        ),
        score=15, flag="cross_border_transfer",
        explanation="International transfer — compliance documentation and FATF checks required",
        weight_category="geography",
    ),
    # R17: FATF high-scrutiny jurisdiction (additional enhanced due diligence)
    RiskRule(
        condition=lambda e: (
            str(e.get("destination_country", "") or "").strip().lower() in _FATF_COUNTRIES
        ),
        score=10, flag="fatf_jurisdiction",
        explanation="Transfer to FATF high-scrutiny jurisdiction — enhanced due diligence required",
        weight_category="geography",
    ),

    # ── TRUST & CONFIDENCE ─────────────────────────────────────────────────────
    # R18: established customer lowers fraud probability
    RiskRule(
        condition=lambda e: e.get("returning_customer") is True,
        score=-15, flag="trusted_customer",
        explanation="Established returning customer — reduced fraud probability",
        weight_category="trust",
    ),
    # R19: low AI confidence signals an unusual or ambiguous request
    #      confidence defaults to 1.0 when absent (rescore_pending path) — never false-fires
    RiskRule(
        condition=lambda e: float(e.get("confidence", 1.0) or 1.0) < 0.7,
        score=10, flag="low_ai_confidence",
        explanation="AI uncertain about this request — may be unusual, complex, or misleading",
        weight_category="trust",
    ),
]

_RISK_LEVELS = [
    (0,  30,  "low"),
    (31, 70,  "medium"),
    (71, 100, "high"),
]


def calculate_risk(intent_data: dict) -> dict:
    """
    Evaluate all risk rules against the merged intent + entity data.

    The input dict is the result of IntentExtraction.model_dump(), which
    has the shape: {intent, confidence, urgency_level, risk_flags, entities: {...}}.
    We flatten entities into the top level so rules can access any key directly.

    For the rescore_pending path (no confidence key): defaults to 1.0 so R19 never
    falsely fires on rescored tasks.
    """
    merged = {**intent_data, **intent_data.get("entities", {})}
    merged.setdefault("confidence", 1.0)

    score        = 0
    flags        = []
    explanations = []
    fired_rules  = []

    for rule in RULES:
        try:
            if rule.condition(merged):
                score += rule.score
                flags.append(rule.flag)
                explanations.append(rule.explanation)
                fired_rules.append({
                    "flag":     rule.flag,
                    "score":    rule.score,
                    "category": rule.weight_category,
                })
        except Exception:
            continue

    raw_score = score
    score     = max(0, min(100, score))
    level     = next(lv for lo, hi, lv in _RISK_LEVELS if lo <= score <= hi)

    log.info(
        "risk_calculated",
        intent=merged.get("intent"),
        raw_score=raw_score,
        final_score=score,
        risk_level=level,
        rules_fired=len(fired_rules),
        detail=fired_rules,
    )

    if raw_score > 100:
        log.warning(
            "risk_score_saturated",
            intent=merged.get("intent"),
            raw_score=raw_score,
            rules_fired=len(fired_rules),
        )

    return {
        "risk_score":          score,
        "risk_level":          level,
        "risk_flags":          flags,
        "risk_explanation":    explanations,
        "escalation_required": score >= 71,
    }
