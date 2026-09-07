"""Public URL fetches pinned to validated DNS results; no browser subrequests."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx

from opencmo.rag.parsing import MAX_BYTES


async def public_target(url: str) -> tuple[httpx.URL, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("invalid_public_url")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("public_url_port_not_allowed")
    host = parsed.hostname.rstrip(".")
    if host.lower() == "localhost" or host.lower().endswith((".local", ".localhost")):
        raise ValueError("private_url_not_allowed")
    rows = await asyncio.get_running_loop().getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(row[4][0] for row in rows))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("private_url_not_allowed")
    return httpx.URL(url).copy_with(host=addresses[0]), host

async def fetch_public_url(url: str) -> tuple[bytes, str, str]:
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
        for _ in range(6):
            pinned, host = await public_target(url)
            async with client.stream("GET", pinned, headers={"Host": host, "User-Agent": "OpenCMO-Knowledge/1.0"},
                                     extensions={"sni_hostname": host}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("invalid_redirect")
                    url = urljoin(url, location)
                    continue
                response.raise_for_status()
                mime = response.headers.get("content-type", "").split(";")[0]
                if mime not in {"text/html", "text/plain", "text/markdown", "application/pdf"}:
                    raise ValueError("unsupported_web_content_type")
                data = bytearray()
                async for part in response.aiter_bytes():
                    data.extend(part)
                    if len(data) > MAX_BYTES:
                        raise ValueError("file_too_large")
                return bytes(data), mime, url
        raise ValueError("too_many_redirects")

