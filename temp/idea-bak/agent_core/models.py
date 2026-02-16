from enum import Enum
from dataclasses import dataclass
from typing import Optional


class IntentType(str, Enum):
    GET_INVOICE = "GET_INVOICE"
    EXPLAIN = "EXPLAIN"


@dataclass
class Intent:
    """
    Normalized representation of user intent.
    Produced by the intent classifier and consumed by the router.
    """
    type: IntentType
    invoice_id: Optional[int] = None
    input_text: Optional[str] = None
