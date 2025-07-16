import json
import os
from datetime import datetime, timedelta
import requests

TOKEN_URL = "https://auth.atlassian.com/oauth/token"


def load_tokens(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Token file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tokens(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_expired(token_data):
    created_at = datetime.fromisoformat(token_data.get("token_created_at"))
    expires_in = int(token_data.get("expires_in", 0))
    expiry_time = created_at + timedelta(seconds=expires_in - 300)
    return datetime.utcnow() >= expiry_time


def refresh_access_token(token_data, path):
    payload = {
        "grant_type": "refresh_token",
        "client_id": token_data["client_id"],
        "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"],
    }
    response = requests.post(TOKEN_URL, json=payload)
    response.raise_for_status()
    new_tokens = response.json()
    token_data["access_token"] = new_tokens["access_token"]
    token_data["expires_in"] = new_tokens.get("expires_in", token_data.get("expires_in"))
    token_data["token_created_at"] = datetime.utcnow().isoformat()
    if "refresh_token" in new_tokens:
        token_data["refresh_token"] = new_tokens["refresh_token"]
    save_tokens(path, token_data)


def get_valid_access_token(token_file):
    token_data = load_tokens(token_file)
    if "access_token" not in token_data:
        raise ValueError("Token file missing access_token")

    if is_expired(token_data):
        refresh_access_token(token_data, token_file)
    else:
        if not token_data.get("token_created_at"):
            token_data["token_created_at"] = datetime.utcnow().isoformat()
            save_tokens(token_file, token_data)
    return token_data["access_token"]
