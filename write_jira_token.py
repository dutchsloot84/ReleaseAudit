import argparse
import json
from datetime import datetime, timezone
import requests

TOKEN_URL = "https://auth.atlassian.com/oauth/token"


def generate_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(TOKEN_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    data["client_id"] = client_id
    data["client_secret"] = client_secret
    data["token_created_at"] = datetime.now(timezone.utc).isoformat()
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate jira_token.json from an OAuth authorization code")
    parser.add_argument("client_id", help="OAuth Client ID")
    parser.add_argument("client_secret", help="OAuth Client Secret")
    parser.add_argument("code", help="Authorization Code from Atlassian")
    parser.add_argument(
        "--redirect-uri",
        default="http://localhost:8080/callback",
        help="Redirect URI used when obtaining the authorization code",
    )
    parser.add_argument(
        "--output",
        default="jira_token.json",
        help="Path to write the token JSON file",
    )
    args = parser.parse_args()

    token_data = generate_token(args.client_id, args.client_secret, args.code, args.redirect_uri)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)
    print(f"\u2705 Saved token to {args.output}")


if __name__ == "__main__":
    main()
