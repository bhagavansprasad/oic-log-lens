from domain_services.invoice_service import InvoiceService


class InvoiceCapability:
    def __init__(self):
        self.service = InvoiceService()

    def get_invoice_by_id(self, invoice_id):
        return self.service.get_invoice_by_id(invoice_id)
