import os
import hashlib
from contextvars import ContextVar

import uvicorn
from mcp.server.fastmcp import FastMCP

# Store the challenge separately for each incoming HTTP request.
current_challenge = ContextVar("current_challenge", default=None)

EMAIL = "25f1001114@ds.study.iitm.ac.in"

mcp = FastMCP("Exam Challenge Server")


class ChallengeHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        challenge = headers.get(b"x-exam-challenge") if False else None
        # ASGI header names are bytes.
        challenge = next(
            (
                value.decode("latin-1")
                for key, value in scope.get("headers", [])
                if key.lower() == b"x-exam-challenge"
            ),
            None,
        )

        token = current_challenge.set(challenge)
        try:
            await self.app(scope, receive, send)
        finally:
            current_challenge.reset(token)


@mcp.tool()
def solve_challenge() -> str:
    """Solve the current exam challenge using the HTTP request header."""
    challenge = current_challenge.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    message = f"{challenge}:{EMAIL}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


app = ChallengeHeaderMiddleware(mcp.streamable_http_app())


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
