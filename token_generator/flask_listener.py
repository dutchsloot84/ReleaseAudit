import threading
from urllib.parse import urlparse

from flask import Flask, request
from werkzeug.serving import make_server


class AuthorizationCodeReceiver:
    """Simple local server to capture OAuth authorization code."""

    def __init__(self, redirect_uri: str):
        parsed = urlparse(redirect_uri)
        self.port = parsed.port or 80
        self.path = parsed.path or "/"
        self.code = None
        self._event = threading.Event()
        self.app = Flask(__name__)

        @self.app.route(self.path)
        def _callback():
            code = request.args.get("code")
            if not code:
                return "Authorization code missing", 400
            self.code = code
            self._event.set()
            shutdown = request.environ.get("werkzeug.server.shutdown")
            if shutdown:
                shutdown()
            return "Authorization received. You may close this window."

    def start(self) -> None:
        """Start the local server."""
        self.server = make_server("localhost", self.port, self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def wait_for_code(self, timeout: int = 300) -> str | None:
        """Wait for the authorization code or timeout."""
        if not self._event.wait(timeout):
            return None
        return self.code
