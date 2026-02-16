import re
from agent_core.models import Intent, IntentType

INVOICE_ID_PATTERN = re.compile(r"\b\d{4,}\b")


def classify_intent(user_input: str) -> Intent:
    """
    Classifies user input into a high-level intent.
    Deterministic, heuristic-based (POC version).
    """
    text = user_input.lower()

    # Invoice intent
    if "invoice" in text:
        match = INVOICE_ID_PATTERN.search(text)
        if match:
            return Intent(
                type=IntentType.GET_INVOICE,
                invoice_id=int(match.group())
            )

    # Explanation / reasoning intent
    if "error" in text or "why" in text or "ora-" in text:
        return Intent(
            type=IntentType.EXPLAIN,
            input_text=user_input
        )

    # Default fallback → explanation
    return Intent(
        type=IntentType.EXPLAIN,
        input_text=user_input
    )
