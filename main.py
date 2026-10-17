
import os
import hashlib
from contextvars import ContextVar

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


# Store the challenge for the current HTTP request.
current_challenge = ContextVar("current_challenge", default=None)

EMAIL = "25f1001114@ds.study.iitm.ac.in"


# Allow local testing and the deployed Render service.
security = TransportSecuritySettings(
    allowed_hosts=[
        "127.0.0.1:8000",
        "localhost:8000",
        "mcp-challenge-server-k48r.onrender.com",
        "mcp-challenge-server-k48r.onrender.com:*",
    ],
    enable_dns_rebinding_protection=True,
)


mcp = FastMCP(
    "Exam Challenge Server",
    transport_security=security,
    stateless_http=True,
)


class ChallengeHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Read X-Exam-Challenge from this HTTP request's headers.
        challenge = next(
            (
                value.decode("latin-1")
                for key, value in scope.get("headers", [])
                if key.lower() == b"x-exam-challenge"
            ),
            None,
        )

        # Set the challenge for this request and restore it afterward.
        token = current_challenge.set(challenge)

        try:
            await self.app(scope, receive, send)
        finally:
            current_challenge.reset(token)


@mcp.tool()
def solve_challenge() -> str:
    """Return the first 16 hex characters of the challenge SHA-256 hash."""
    challenge = current_challenge.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    message = f"{challenge}:{EMAIL}"

    return hashlib.sha256(
        message.encode("utf-8")
    ).hexdigest()[:16]


app = ChallengeHeaderMiddleware(
    mcp.streamable_http_app()
)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
