from pydantic import BaseModel, Field
from typing import Literal, Any


class IntentExtraction(BaseModel):
    intent: Literal[
        "send_money",
        "verify_document",
        "hire_service",
        "airport_transfer",
        "general_inquiry",
    ]
    confidence:    float = Field(ge=0.0, le=1.0)
    entities:      dict[str, Any] = Field(default_factory=dict)
    urgency_level: Literal["low", "medium", "high"]
    risk_flags:    list[str] = Field(default_factory=list)
