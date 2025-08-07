import json
import logging
import threading
import webbrowser
from pathlib import Path
from tkinter import Tk, ttk, messagebox, StringVar
from urllib.parse import urlencode, quote_plus

import requests

from flask_listener import AuthorizationCodeReceiver
from oauth_client import exchange_code_for_token

logging.basicConfig(level=logging.INFO)


class TokenGeneratorGUI:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("Jira OAuth Token Generator")

        self.client_id_var = StringVar()
        self.client_secret_var = StringVar()
        self.redirect_var = StringVar(value="http://localhost:8080/callback")

        ttk.Label(root, text="Client ID:").grid(row=0, column=0, sticky="e", pady=5, padx=5)
        ttk.Entry(root, textvariable=self.client_id_var, width=40).grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(root, text="Client Secret:").grid(row=1, column=0, sticky="e", pady=5, padx=5)
        ttk.Entry(root, textvariable=self.client_secret_var, show="*", width=40).grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(root, text="Redirect URI:").grid(row=2, column=0, sticky="e", pady=5, padx=5)
        ttk.Entry(root, textvariable=self.redirect_var, width=40).grid(row=2, column=1, pady=5, padx=5)

        ttk.Button(root, text="Launch Authorization", command=self.launch).grid(row=3, column=0, columnspan=2, pady=10)

    def launch(self) -> None:
        threading.Thread(target=self._auth_flow, daemon=True).start()

    def _auth_flow(self) -> None:
        client_id = self.client_id_var.get().strip()
        client_secret = self.client_secret_var.get().strip()
        redirect_uri = self.redirect_var.get().strip()

        if not client_id or not client_secret:
            messagebox.showerror("Input Error", "Client ID and Client Secret are required")
            return

        receiver = AuthorizationCodeReceiver(redirect_uri)
        try:
            receiver.start()
        except OSError:
            messagebox.showerror("Port In Use", f"Cannot start local server on port {receiver.port}")
            return

        params = {
            "audience": "api.atlassian.com",
            "client_id": client_id,
            "scope": "read:jira-user read:jira-work write:jira-work offline_access",
            "redirect_uri": redirect_uri,
            "state": "xyz123",
            "response_type": "code",
            "prompt": "consent",
        }
        url = "https://auth.atlassian.com/authorize?" + urlencode(params, quote_via=quote_plus)
        webbrowser.open(url)

        code = receiver.wait_for_code()
        if not code:
            messagebox.showerror("Timeout", "No authorization code received")
            return

        try:
            token_data = exchange_code_for_token(client_id, client_secret, code, redirect_uri)
        except requests.HTTPError as exc:
            logging.exception("Token exchange failed")
            messagebox.showerror("Error", f"Token request failed: {exc.response.text}")
            return
        except Exception as exc:
            logging.exception("Token exchange failed")
            messagebox.showerror("Error", str(exc))
            return

        Path("jira_token.json").write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        messagebox.showinfo("Success", "Token saved to jira_token.json")


def main() -> None:
    root = Tk()
    TokenGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
