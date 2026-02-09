import os
from requests.auth import HTTPBasicAuth


def get_auth():
    username = os.getenv("ORACLE_CLOUD_USERNAME")
    password = os.getenv("ORACLE_CLOUD_PASSWORD")

    if not username or not password:
        raise RuntimeError("Oracle credentials not set")

    return HTTPBasicAuth(username, password)
