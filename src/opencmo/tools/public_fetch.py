"""Bounded public-web requests for agent tools (no optional RAG dependencies)."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit

import httpx

FETCH_TIMEOUT = 15.0
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_REDIRECTS = 5


async def _public_target(url: str) -> tuple[httpx.URL, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("invalid_public_url")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("public_url_port_not_allowed")
    host = parsed.hostname.rstrip(".")
    if host.lower() == "localhost" or host.lower().endswith((".local", ".localhost")):
        raise ValueError("private_url_not_allowed")
    rows = await asyncio.get_running_loop().getaddrinfo(
        host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM,
    )
    addresses = list(dict.fromkeys(row[4][0] for row in rows))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("private_url_not_allowed")
    return httpx.URL(url).copy_with(host=addresses[0]), host


async def fetch_public_text(url: str, *, deadline: float | None = None) -> httpx.Response:
    """Fetch under a whole-operation deadline; return only a bounded, buffered body.

    A caller doing multiple requests can share one monotonic deadline. DNS is
    checked on every hop and the connection uses the validated IP, while Host
    and TLS SNI keep the original hostname. Proxy environment variables are ignored.
    """
    if deadline is None:
        deadline = time.monotonic() + FETCH_TIMEOUT
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("public_fetch_deadline_exceeded")
    try:
        return await asyncio.wait_for(_fetch(url), timeout=remaining)
    except asyncio.TimeoutError as exc:
        raise TimeoutError("public_fetch_deadline_exceeded") from exc


async def _fetch(url: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=False, trust_env=False) as client:
        for hop in range(MAX_REDIRECTS + 1):
            pinned, host = await _public_target(url)
            async with client.stream(
                "GET", pinned, headers={"Host": host, "User-Agent": "OpenCMO-Tools/1.0", "Accept-Encoding": "identity"},
                extensions={"sni_hostname": host},
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("invalid_redirect")
                    if hop == MAX_REDIRECTS:
                        raise ValueError("too_many_redirects")
                    url = urljoin(url, location)
                    continue
                # Avoid allocating an unbounded decompression bomb before the size check.
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ValueError("unsupported_content_encoding")
                length = response.headers.get("content-length")
                if length is not None and int(length) > MAX_RESPONSE_BYTES:
                    raise ValueError("response_too_large")
                data = bytearray()
                async for part in response.aiter_raw(chunk_size=65536):
                    if len(data) + len(part) > MAX_RESPONSE_BYTES:
                        raise ValueError("response_too_large")
                    data.extend(part)
                # The stream belongs to the pinned URL; expose the validated logical URL.
                return httpx.Response(
                    response.status_code, headers=response.headers, content=bytes(data),
                    request=httpx.Request("GET", url),
                )
    raise ValueError("too_many_redirects")
