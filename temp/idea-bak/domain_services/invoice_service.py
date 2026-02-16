from data_access.rest_client import RestClient


class InvoiceService:
    def __init__(self):
        self.client = RestClient()

    def get_invoice_by_id(self, invoice_id: int):
        endpoint = "/fscmRestApi/resources/11.13.18.05/invoices"
        params = {
            "q": f"InvoiceId={invoice_id}",
            "onlyData": "true"
        }

        response = self.client.get(endpoint, params)

        items = response.get("items", [])
        if not items:
            return None

        return self._map_invoice(items[0])

    def _map_invoice(self, fusion_invoice):
        return fusion_invoice

        return {
            "invoiceId": fusion_invoice.get("InvoiceId"),
            "invoiceNumber": fusion_invoice.get("InvoiceNumber"),
            "supplier": fusion_invoice.get("Supplier"),
            "supplierNumber": fusion_invoice.get("SupplierNumber"),
            "invoiceAmount": fusion_invoice.get("InvoiceAmount"),
            "invoiceDate": fusion_invoice.get("InvoiceDate"),
            "status": fusion_invoice.get("InvoiceStatus")
        }
