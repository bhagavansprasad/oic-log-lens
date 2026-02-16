from agent_core.models import Intent, IntentType
from capabilities.invoice_capability import InvoiceCapability
from capabilities.explanation_capability import ExplanationCapability


class IntentRouter:
    """
    Routes a classified Intent to the appropriate capability.
    """

    def __init__(self):
        self.invoice_capability = InvoiceCapability()
        self.explanation_capability = ExplanationCapability()

    def route(self, intent: Intent):
        if intent.type == IntentType.GET_INVOICE:
            return self.invoice_capability.get_invoice_by_id(
                intent.invoice_id
            )

        if intent.type == IntentType.EXPLAIN:
            return self.explanation_capability.explain(
                intent.input_text
            )

        raise ValueError(f"Unsupported intent type: {intent.type}")
