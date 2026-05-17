"""Email verification code storage — generation, hashing, consumption, rate limits."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from opencmo.storage._db import get_db

logger = logging.getLogger(__name__)

CODE_LENGTH = 6
DEFAULT_TTL_SECONDS = 600  # 10 minutes
MAX_ATTEMPTS = 5
DEFAULT_RESEND_COOLDOWN_SECONDS = 60
DEFAULT_HOURLY_SEND_LIMIT = 5


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _sqlite_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_sqlite_ts(value: str | None) -> datetime | None:
    """Parse a sqlite TEXT timestamp as UTC.

    SQLite stores ``datetime('now')`` as ``YYYY-MM-DD HH:MM:SS`` without a
    timezone designator, but the value is always UTC. ``datetime.fromisoformat``
    treats it as naive, so we must attach ``timezone.utc`` rather than calling
    ``.astimezone()`` (which would interpret the naive value as *local* time
    and shift it).
    """
    if not value:
        return None
    raw = value.strip()
    # If a Z or +offset is already present, fromisoformat handles it correctly.
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hash_code(code: str) -> str:
    """SHA-256 of (code + per-row salt would be overkill for 6 digits).

    Codes are short-lived (10 min) and rate-limited (5 attempts), so a plain
    SHA-256 is sufficient and constant-time-comparable via hmac.compare_digest.
    """
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    """6 digits, leading zeros allowed (e.g. '004217')."""
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


async def create_code(
    user_id: int,
    purpose: str = "signup",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Generate a new verification code, invalidate prior unconsumed ones, return plaintext.

    Caller is responsible for delivering the plaintext code to the user.
    """
    code = _generate_code()
    code_hash = _hash_code(code)
    expires_at = _sqlite_ts(_utc_now() + timedelta(seconds=ttl_seconds))

    db = await get_db()
    try:
        # Invalidate any prior unconsumed codes for the same purpose so the
        # user can't try an old one after requesting a resend.
        await db.execute(
            """UPDATE email_verifications
               SET consumed_at = datetime('now')
               WHERE user_id = ? AND purpose = ? AND consumed_at IS NULL""",
            (user_id, purpose),
        )
        await db.execute(
            """INSERT INTO email_verifications (user_id, code_hash, purpose, expires_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, code_hash, purpose, expires_at),
        )
        await db.commit()
    finally:
        await db.close()

    return code


async def consume_code(user_id: int, code: str, purpose: str = "signup") -> dict:
    """Try to consume a verification code.

    Returns:
        {"ok": True} on success.
        {"ok": False, "error": "<code>", "remaining_attempts": int} on failure.

    Errors: ``no_pending_code``, ``code_expired``, ``code_invalid``, ``code_locked``.
    """
    code = (code or "").strip()
    if not code:
        return {"ok": False, "error": "code_invalid", "remaining_attempts": MAX_ATTEMPTS}

    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, code_hash, expires_at, attempts
               FROM email_verifications
               WHERE user_id = ? AND purpose = ? AND consumed_at IS NULL
               ORDER BY id DESC
               LIMIT 1""",
            (user_id, purpose),
        )
        row = await cursor.fetchone()
        if not row:
            return {"ok": False, "error": "no_pending_code", "remaining_attempts": 0}

        row_id, code_hash, expires_at_raw, attempts = int(row[0]), row[1], row[2], int(row[3] or 0)
        expires_at = _parse_sqlite_ts(expires_at_raw)

        if attempts >= MAX_ATTEMPTS:
            return {"ok": False, "error": "code_locked", "remaining_attempts": 0}

        if not expires_at or expires_at <= _utc_now():
            return {"ok": False, "error": "code_expired", "remaining_attempts": 0}

        if not hmac.compare_digest(code_hash, _hash_code(code)):
            new_attempts = attempts + 1
            await db.execute(
                "UPDATE email_verifications SET attempts = ? WHERE id = ?",
                (new_attempts, row_id),
            )
            await db.commit()
            remaining = max(0, MAX_ATTEMPTS - new_attempts)
            if remaining <= 0:
                return {"ok": False, "error": "code_locked", "remaining_attempts": 0}
            return {"ok": False, "error": "code_invalid", "remaining_attempts": remaining}

        await db.execute(
            "UPDATE email_verifications SET consumed_at = datetime('now') WHERE id = ?",
            (row_id,),
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


async def recent_send_count(
    user_id: int,
    purpose: str,
    within_seconds: int = 3600,
) -> int:
    """Number of codes issued for (user_id, purpose) in the trailing window."""
    cutoff = _sqlite_ts(_utc_now() - timedelta(seconds=within_seconds))
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM email_verifications
               WHERE user_id = ? AND purpose = ? AND created_at >= ?""",
            (user_id, purpose, cutoff),
        )
        row = await cursor.fetchone()
        return int(row[0] or 0)
    finally:
        await db.close()


async def last_send_at(user_id: int, purpose: str) -> datetime | None:
    """Timestamp of the most recent code creation for (user_id, purpose)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT created_at FROM email_verifications
               WHERE user_id = ? AND purpose = ?
               ORDER BY id DESC LIMIT 1""",
            (user_id, purpose),
        )
        row = await cursor.fetchone()
        return _parse_sqlite_ts(row[0]) if row else None
    finally:
        await db.close()


async def mark_user_verified(user_id: int) -> None:
    """Mark a user as email-verified and ensure they are active."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE users
               SET email_verified_at = datetime('now'),
                   status = 'active'
               WHERE id = ?""",
            (user_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def is_user_verified(user_id: int) -> bool:
    """Whether a user has completed email verification."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT email_verified_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return bool(row and row[0])
    finally:
        await db.close()
