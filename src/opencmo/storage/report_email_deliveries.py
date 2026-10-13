"""Durable report delivery claims; never expire a potentially accepted send."""

from __future__ import annotations

import json

from opencmo.storage._db import get_db


async def claim_delivery(
    *, account_id: int, project_id: int, report_id: int, recipient: str, locale: str, resend_key: str
) -> tuple[bool, dict]:
    """Atomically claim one delivery, or return its persisted state/result.

    A sending claim cannot be reclaimed: a terminated SMTP worker may already
    have delivered its message. A deliberate resend uses a new resend_key.
    """
    identity = (account_id, project_id, report_id, recipient, locale, resend_key)
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT OR IGNORE INTO report_email_deliveries
               (account_id, project_id, report_id, recipient, locale, resend_key)
               VALUES (?, ?, ?, ?, ?, ?)""",
            identity,
        )
        claimed = cursor.rowcount == 1
        await db.commit()
        cursor = await db.execute(
            """SELECT id, status, result_json FROM report_email_deliveries
               WHERE account_id = ? AND project_id = ? AND report_id = ?
                 AND recipient = ? AND locale = ? AND resend_key = ?""",
            identity,
        )
        row = await cursor.fetchone()
        return claimed, {"id": row[0], "status": row[1], "result": json.loads(row[2])}
    finally:
        await db.close()


async def finish_delivery(delivery_id: int, *, status: str, result: dict) -> None:
    if status not in {"sent", "uncertain"}:
        raise ValueError("Invalid delivery outcome")
    db = await get_db()
    try:
        await db.execute(
            """UPDATE report_email_deliveries
               SET status = ?, result_json = ?, updated_at = datetime('now')
               WHERE id = ? AND status = 'sending'""",
            (status, json.dumps(result), delivery_id),
        )
        await db.commit()
    finally:
        await db.close()
