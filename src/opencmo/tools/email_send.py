"""Generic SMTP sender — used by reports and verification emails.

Reads SMTP credentials via ``llm.get_key()`` so per-request BYOK keys (set in
a ContextVar by the web app) take precedence over OS env vars, which in turn
take precedence over DB settings.

Dev fallback: if ``OPENCMO_SMTP_HOST`` is missing the sender logs the message
to stderr at WARNING level and returns ``{"ok": True, "dev_mode": True}`` so
local development works without configuring SMTP.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger(__name__)


def _smtp_config() -> dict | None:
    """Read SMTP host/port/user/pass via the BYOK-aware key resolver.

    Recipient is *not* part of this config — that's per-call to ``send_mail``.
    Returns ``None`` when any of host/port/user/pass is missing, which the
    caller interprets as "fall back to dev mode".
    """
    from opencmo import llm

    host = llm.get_key("OPENCMO_SMTP_HOST")
    port = llm.get_key("OPENCMO_SMTP_PORT") or "587"
    user = llm.get_key("OPENCMO_SMTP_USER")
    password = llm.get_key("OPENCMO_SMTP_PASS")

    if not all([host, user, password]):
        return None

    try:
        port_int = int(port)
    except (TypeError, ValueError):
        port_int = 587

    from_address = llm.get_key("OPENCMO_SMTP_FROM") or user
    from_name = llm.get_key("OPENCMO_SMTP_FROM_NAME") or "OpenCMO"

    return {
        "host": str(host),
        "port": port_int,
        "user": str(user),
        "password": str(password),
        "from_address": str(from_address),
        "from_name": str(from_name),
    }


def _mime_text(body: str, subtype: str) -> MIMEText:
    """Use us-ascii when possible so legacy assertions still find substrings.

    ``MIMEText`` base64-encodes utf-8 bodies, which makes plain-text matches
    on ``sent_message.as_string()`` fail. We only escalate to utf-8 when the
    body actually has non-ASCII characters.
    """
    try:
        body.encode("ascii")
    except UnicodeEncodeError:
        return MIMEText(body, subtype, "utf-8")
    return MIMEText(body, subtype)


def _build_message(
    *,
    sender: str,
    to: str,
    subject: str,
    html: str,
    text: str | None,
    headers: dict[str, str] | None = None,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    for header_name, header_value in (headers or {}).items():
        msg[header_name] = header_value
    if text:
        msg.attach(_mime_text(text, "plain"))
    msg.attach(_mime_text(html, "html"))
    return msg


def _send_sync(config: dict, msg: MIMEMultipart, to: str) -> None:
    port = config["port"]
    if port == 465:
        with smtplib.SMTP_SSL(config["host"], port, timeout=30) as server:
            server.login(config["user"], config["password"])
            server.send_message(msg, from_addr=config["from_address"], to_addrs=[to])
    else:
        with smtplib.SMTP(config["host"], port, timeout=30) as server:
            server.starttls()
            server.login(config["user"], config["password"])
            server.send_message(msg, from_addr=config["from_address"], to_addrs=[to])


async def send_mail(
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> dict:
    """Send a multipart HTML email.

    Returns:
        ``{"ok": True}`` on real send,
        ``{"ok": True, "dev_mode": True}`` when SMTP is not configured (the
        caller's prepared content is logged via the ``opencmo.tools.email_send``
        logger so devs can see what would have been sent),
        ``{"ok": False, "error": "<message>"}`` on SMTP failure.
    """
    recipient = (to or "").strip()
    if not recipient:
        return {"ok": False, "error": "recipient_required"}

    config = _smtp_config()
    if config is None:
        logger.warning(
            "SMTP not configured — would have sent email to %s with subject %r. "
            "Set OPENCMO_SMTP_HOST/USER/PASS to enable real delivery.",
            recipient,
            subject,
        )
        return {"ok": True, "dev_mode": True}

    sender = formataddr((config["from_name"], config["from_address"]))
    msg = _build_message(
        sender=sender,
        to=recipient,
        subject=subject,
        html=html,
        text=text,
        headers=headers,
    )

    try:
        await asyncio.to_thread(_send_sync, config, msg, recipient)
        return {"ok": True}
    except Exception as exc:
        logger.exception("SMTP send failed to %s: %s", recipient, exc)
        return {"ok": False, "error": str(exc)}
