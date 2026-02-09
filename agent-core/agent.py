from capabilities.invoice_capability import InvoiceCapability


class Agent:
    def __init__(self):
        self.invoice_capability = InvoiceCapability()

    def handle_get_invoice(self, invoice_id):
        invoice = self.invoice_capability.get_invoice_by_id(invoice_id)

        if not invoice:
            return f"No invoice found for Invoice ID {invoice_id}"

        return invoice
