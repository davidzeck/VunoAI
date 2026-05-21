ROUTING: dict[str, str] = {
    "send_money":      "Finance Team",
    "verify_document": "Legal & Compliance",
    "hire_service":    "Operations Team",
    "airport_transfer":"Logistics Team",
    "general_inquiry": "Support Team",
}


def assign_team(intent: str) -> str:
    return ROUTING.get(intent, "Support Team")
