"""Alibaba Cloud Function Compute (FC) handler.

Tech Design: "部署环境: 阿里云函数计算 (FC) Serverless"

Wraps the FastAPI app as an FC-compatible handler using ASGI-to-FC bridge.

Usage:
    Set FC runtime to Python 3.10+, handler to `fc_handler.handler`.
    The FC event is translated to ASGI and passed to the FastAPI app.
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def handler(environ, start_response):
    """FC HTTP handler using ASGI middleware.

    Minimal ASGI-to-WSGI bridge for Alibaba Cloud FC.
    For production, consider using mangum or a proper ASGI adapter.
    """
    import json
    from main import app

    # ── Parse FC event into ASGI scope ──
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    query_string = environ.get("QUERY_STRING", "")
    headers_raw = environ.get("fc.headers", {}) or {}

    # Normalize headers to ASGI format
    headers: list[tuple[bytes, bytes]] = [
        (k.encode("latin-1"), v.encode("latin-1"))
        for k, v in headers_raw.items()
    ]

    server_name = environ.get("fc.context", {}).get("service", {}).get("name", "fc")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query_string.encode("latin-1"),
        "headers": headers,
        "server": (server_name, 443),
        "client": ("", 0),
    }

    # Collect response
    response_status = [200]
    response_headers: list[tuple[bytes, bytes]] = []
    response_body_chunks: list[bytes] = []

    async def receive():
        body = environ.get("wsgi.input")
        if body:
            content = body.read()
        else:
            content = b""
        return {
            "type": "http.request",
            "body": content,
            "more_body": False,
        }

    async def send(message):
        if message["type"] == "http.response.start":
            response_status[0] = message["status"]
            response_headers.clear()
            response_headers.extend(
                (k.decode("latin-1"), v.decode("latin-1"))
                for k, v in message.get("headers", [])
            )
        elif message["type"] == "http.response.body":
            response_body_chunks.append(message.get("body", b""))

    # Run ASGI app
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(app(scope, receive, send))
    finally:
        loop.close()

    # Write WSGI response
    status_str = f"{response_status[0]} OK"
    start_response(status_str, response_headers)
    return [b"".join(response_body_chunks)]
