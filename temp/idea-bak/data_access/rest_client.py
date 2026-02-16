import os
import requests
from data_access.auth import get_auth


class RestClient:
    def __init__(self):
        self.mode = os.getenv("REST_CLIENT_MODE", "REAL")
        self.base_url = "https://fa-esll-dev37-saasfademo1.ds-fa.oraclepdemos.com"
        self.auth = get_auth()
        self.headers = {"Accept": "application/json"}

    def get(self, endpoint, params):
        if self.mode == "MOCK":
            return self._mock_response()

        return self._real_get(endpoint, params)

    def _real_get(self, endpoint, params):
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()

    def _mock_response(self):
        return {
            "items": [
                {
                    "InvoiceId": 493527,
                    "InvoiceNumber": "ERS-50742-182312",
                    "Supplier": "Lee Enterprises",
                    "SupplierNumber": "1252",
                    "InvoiceAmount": 4500,
                    "InvoiceDate": "2024-01-15",
                    "InvoiceStatus": "APPROVED"
                }
            ]
        }
