import json
import os
from datetime import datetime, timedelta, timezone
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

def _parse_created_at(token_data):
    created_at = datetime.fromisoformat(token_data.get("token_created_at"))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at

def is_expired(token_data):
    created_at = _parse_created_at(token_data)
    expires_in = int(token_data.get("expires_in", 0))
    expiry_time = created_at + timedelta(seconds=expires_in - 300)  # 5 min early
    return datetime.now(timezone.utc) >= expiry_time

def warn_refresh_token_expiry(token_data):
    created_at = _parse_created_at(token_data)
    refresh_expiry = created_at + timedelta(days=30)
    remaining = refresh_expiry - datetime.now(timezone.utc)
    days_left = remaining.days
    if days_left < 5:
        print(
            f"\u26A0\uFE0F Warning: refresh_token expires in {days_left} days. Consider reauthorizing soon."
        )

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
    token_data["token_created_at"] = datetime.now(timezone.utc).isoformat()
    if "refresh_token" in new_tokens:
        token_data["refresh_token"] = new_tokens["refresh_token"]
    save_tokens(path, token_data)

def get_valid_access_token(token_file, force_refresh=False):
    token_data = load_tokens(token_file)
    if "access_token" not in token_data:
        raise ValueError("Token file missing access_token")

    if force_refresh:
        print("🔄 Force-refreshing access token...")
        refresh_access_token(token_data, token_file)
    elif is_expired(token_data):
        print("🔁 Access token expired. Refreshing...")
        refresh_access_token(token_data, token_file)

    warn_refresh_token_expiry(token_data)
    return token_data["access_token"]
