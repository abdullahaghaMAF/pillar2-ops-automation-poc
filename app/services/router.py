import re
from typing import Tuple

def classify(message: str) -> Tuple[str, bool]:
    """
    Returns: (category, needs_approval)
    """
    m = message.lower()

    # expense / purchase signals
    expense_keywords = ["buy", "purchase", "invoice", "card", "pay", "subscription", "laptop", "phone", "tablet", "amazon"]
    if any(k in m for k in expense_keywords):
        return ("expense_purchase", True)

    # default
    return ("general_task", False)

def make_title(message: str) -> str:
    # Keep it short for Todoist title
    cleaned = re.sub(r"\s+", " ", message).strip()
    return cleaned[:70] + ("..." if len(cleaned) > 70 else "")
