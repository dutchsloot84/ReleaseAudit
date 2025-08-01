import json
from datetime import datetime, timezone
from typing import Dict

import requests

TOKEN_URL = "https://auth.atlassian.com/oauth/token"


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict:
    """Exchange an authorization code for OAuth tokens."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(TOKEN_URL, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    data["client_id"] = client_id
    data["client_secret"] = client_secret
    data["token_created_at"] = datetime.now(timezone.utc).isoformat()
    return data
