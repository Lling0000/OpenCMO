"""Account, user, session, and trial-usage storage."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from opencmo.storage._db import get_db
from opencmo.storage.waitlist import is_valid_email

SESSION_COOKIE_NAME = "opencmo_session"
SESSION_DAYS = 30
MIN_PASSWORD_LENGTH = 8


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _sqlite_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_sqlite_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def get_signup_mode() -> str:
    value = os.environ.get("OPENCMO_SIGNUP_MODE", "open").strip().lower()
    return value if value in {"open", "closed", "invite"} else "open"


def get_trial_config() -> dict:
    return {
        "trial_days": _env_int("OPENCMO_TRIAL_DAYS", 14),
        "max_projects": _env_int("OPENCMO_FREE_MAX_PROJECTS", 3),
        "daily_scan_limit": _env_int("OPENCMO_FREE_DAILY_SCANS", 3),
        "monthly_report_limit": _env_int("OPENCMO_FREE_MONTHLY_REPORTS", 10),
    }


def _cookie_secret() -> str:
    return os.environ.get("OPENCMO_COOKIE_SECRET", "replace-me")


def hash_session_token(token: str) -> str:
    return hmac.new(_cookie_secret().encode(), token.encode(), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    try:
        import bcrypt  # type: ignore

        return "bcrypt$" + bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except Exception:
        salt = secrets.token_hex(16)
        digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1).hex()
        return f"scrypt$16384$8$1${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or stored_hash == "!unusable":
        return False
    if stored_hash.startswith("bcrypt$"):
        try:
            import bcrypt  # type: ignore

            return bool(bcrypt.checkpw(password.encode(), stored_hash.removeprefix("bcrypt$").encode()))
        except Exception:
            return False
    if stored_hash.startswith("scrypt$"):
        try:
            _, n_raw, r_raw, p_raw, salt, expected = stored_hash.split("$", 5)
            digest = hashlib.scrypt(
                password.encode(),
                salt=salt.encode(),
                n=int(n_raw),
                r=int(r_raw),
                p=int(p_raw),
            ).hex()
            return hmac.compare_digest(digest, expected)
        except Exception:
            return False
    return False


def _user_from_row(row) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "status": row[4],
        "created_at": row[5],
        "last_login_at": row[6],
    }


def _account_from_row(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "plan": row[2],
        "status": row[3],
        "trial_started_at": row[4],
        "trial_ends_at": row[5],
        "max_projects": row[6],
        "daily_scan_limit": row[7],
        "monthly_report_limit": row[8],
        "created_at": row[9],
    }


async def get_admin_account_id() -> int:
    admin_email = os.environ.get("OPENCMO_ADMIN_EMAIL", "hello@aidcmo.com").strip().lower()
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.id
               FROM accounts a
               JOIN account_members m ON m.account_id = a.id
               JOIN users u ON u.id = m.user_id
               WHERE u.email = ?
               ORDER BY a.id
               LIMIT 1""",
            (admin_email,),
        )
        row = await cursor.fetchone()
        if row:
            return int(row[0])
        cursor = await db.execute("SELECT id FROM accounts ORDER BY id LIMIT 1")
        row = await cursor.fetchone()
        if row:
            return int(row[0])
        raise RuntimeError("admin account bootstrap failed")
    finally:
        await db.close()


async def get_user_account(user_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.id, a.name, a.plan, a.status, a.trial_started_at, a.trial_ends_at,
                      a.max_projects, a.daily_scan_limit, a.monthly_report_limit, a.created_at
               FROM accounts a
               JOIN account_members m ON m.account_id = a.id
               WHERE m.user_id = ?
               ORDER BY CASE m.role WHEN 'owner' THEN 0 ELSE 1 END, a.id
               LIMIT 1""",
            (user_id,),
        )
        row = await cursor.fetchone()
        return _account_from_row(row) if row else None
    finally:
        await db.close()


async def create_user_with_account(email: str, password: str, name: str = "") -> tuple[dict, dict]:
    normalized = (email or "").strip().lower()
    admin_email = os.environ.get("OPENCMO_ADMIN_EMAIL", "hello@aidcmo.com").strip().lower()
    if not is_valid_email(normalized):
        raise ValueError("invalid_email")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError("password_too_short")

    config = get_trial_config()
    now = _utc_now()
    trial_ends = now + timedelta(days=config["trial_days"])
    db = await get_db()
    try:
        existing = await db.execute("SELECT id, password_hash FROM users WHERE email = ?", (normalized,))
        row = await existing.fetchone()
        if row and row[1] == "!unusable" and normalized == admin_email:
            raise ValueError("email_exists")
        if row and row[1] != "!unusable":
            raise ValueError("email_exists")

        if row:
            user_id = int(row[0])
            await db.execute(
                "UPDATE users SET password_hash = ?, name = ?, status = 'active' WHERE id = ?",
                (hash_password(password), name.strip(), user_id),
            )
        else:
            cursor = await db.execute(
                """INSERT INTO users (email, password_hash, name, role, status)
                   VALUES (?, ?, ?, ?, 'active')""",
                (
                    normalized,
                    hash_password(password),
                    name.strip(),
                    "user",
                ),
            )
            user_id = int(cursor.lastrowid)

        account_name = name.strip() or normalized.split("@", 1)[0]
        cursor = await db.execute(
            """SELECT a.id
               FROM accounts a
               JOIN account_members m ON m.account_id = a.id
               WHERE m.user_id = ?
               LIMIT 1""",
            (user_id,),
        )
        account_row = await cursor.fetchone()
        if account_row:
            account_id = int(account_row[0])
        else:
            cursor = await db.execute(
                """INSERT INTO accounts (
                       name, plan, status, trial_started_at, trial_ends_at,
                       max_projects, daily_scan_limit, monthly_report_limit
                   )
                   VALUES (?, 'free_trial', 'active', ?, ?, ?, ?, ?)""",
                (
                    account_name,
                    _sqlite_ts(now),
                    _sqlite_ts(trial_ends),
                    config["max_projects"],
                    config["daily_scan_limit"],
                    config["monthly_report_limit"],
                ),
            )
            account_id = int(cursor.lastrowid)
            await db.execute(
                "INSERT OR IGNORE INTO account_members (account_id, user_id, role) VALUES (?, ?, 'owner')",
                (account_id, user_id),
            )

        await db.commit()
    finally:
        await db.close()

    user = await get_user_by_id(user_id)
    account = await get_account(account_id)
    if not user or not account:
        raise RuntimeError("signup failed")
    return user, account


async def get_user_by_id(user_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, email, name, role, status, created_at, last_login_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return _user_from_row(row) if row else None
    finally:
        await db.close()


async def get_account(account_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, name, plan, status, trial_started_at, trial_ends_at,
                      max_projects, daily_scan_limit, monthly_report_limit, created_at
               FROM accounts WHERE id = ?""",
            (account_id,),
        )
        row = await cursor.fetchone()
        return _account_from_row(row) if row else None
    finally:
        await db.close()


async def authenticate_user(email: str, password: str) -> tuple[dict, dict] | None:
    normalized = (email or "").strip().lower()
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, email, password_hash, name, role, status, created_at, last_login_at
               FROM users WHERE email = ?""",
            (normalized,),
        )
        row = await cursor.fetchone()
        if not row or not verify_password(password or "", row[2]):
            return None
        user = {
            "id": row[0],
            "email": row[1],
            "name": row[3],
            "role": row[4],
            "status": row[5],
            "created_at": row[6],
            "last_login_at": row[7],
        }
        if user["status"] != "active":
            return None
        await db.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user["id"],))
        await db.commit()
    finally:
        await db.close()

    account = await get_user_account(user["id"])
    if not account or account["status"] != "active":
        return None
    return user, account


async def create_session(user_id: int) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(token)
    expires_at = _sqlite_ts(_utc_now() + timedelta(days=SESSION_DAYS))
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, token_hash, expires_at),
        )
        await db.commit()
    finally:
        await db.close()
    return token, expires_at


async def delete_session(token: str) -> None:
    if not token:
        return
    db = await get_db()
    try:
        await db.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_session_token(token),))
        await db.commit()
    finally:
        await db.close()


async def get_session_context(token: str) -> dict | None:
    if not token:
        return None
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT u.id, u.email, u.name, u.role, u.status, u.created_at, u.last_login_at,
                      a.id, a.name, a.plan, a.status, a.trial_started_at, a.trial_ends_at,
                      a.max_projects, a.daily_scan_limit, a.monthly_report_limit, a.created_at,
                      s.expires_at
               FROM sessions s
               JOIN users u ON u.id = s.user_id
               JOIN account_members m ON m.user_id = u.id
               JOIN accounts a ON a.id = m.account_id
               WHERE s.token_hash = ?
               ORDER BY CASE m.role WHEN 'owner' THEN 0 ELSE 1 END, a.id
               LIMIT 1""",
            (hash_session_token(token),),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        expires_at = _parse_sqlite_ts(row[17])
        if expires_at and expires_at <= _utc_now():
            await db.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_session_token(token),))
            await db.commit()
            return None
        user = {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "role": row[3],
            "status": row[4],
            "created_at": row[5],
            "last_login_at": row[6],
        }
        account = {
            "id": row[7],
            "name": row[8],
            "plan": row[9],
            "status": row[10],
            "trial_started_at": row[11],
            "trial_ends_at": row[12],
            "max_projects": row[13],
            "daily_scan_limit": row[14],
            "monthly_report_limit": row[15],
            "created_at": row[16],
        }
        if user["status"] != "active" or account["status"] != "active":
            return None
        return {"user": user, "account": account, "is_admin": user["role"] == "admin"}
    finally:
        await db.close()


def trial_status(account: dict, *, project_count: int = 0, scans_today: int = 0, reports_this_month: int = 0) -> dict:
    ends_at = _parse_sqlite_ts(account.get("trial_ends_at"))
    now = _utc_now()
    remaining_days = 0
    if ends_at:
        remaining_days = max(0, (ends_at.date() - now.date()).days)
    return {
        "plan": account.get("plan", "free_trial"),
        "status": account.get("status", "active"),
        "trial_started_at": account.get("trial_started_at"),
        "trial_ends_at": account.get("trial_ends_at"),
        "remaining_days": remaining_days,
        "projects": {"used": project_count, "limit": account.get("max_projects", 0)},
        "daily_scans": {"used": scans_today, "limit": account.get("daily_scan_limit", 0)},
        "monthly_reports": {"used": reports_this_month, "limit": account.get("monthly_report_limit", 0)},
    }


async def count_projects_for_account(account_id: int) -> int:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM projects WHERE account_id = ?", (account_id,))
        row = await cursor.fetchone()
        return int(row[0] or 0)
    finally:
        await db.close()


async def count_usage_events(account_id: int, event_type: str, since: datetime) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM usage_events
               WHERE account_id = ? AND event_type = ? AND created_at >= ?""",
            (account_id, event_type, _sqlite_ts(since)),
        )
        row = await cursor.fetchone()
        return int(row[0] or 0)
    finally:
        await db.close()


async def get_usage_status(account_id: int) -> dict:
    account = await get_account(account_id)
    if not account:
        raise ValueError("account_not_found")
    now = _utc_now()
    start_day = now.replace(hour=0, minute=0, second=0)
    start_month = now.replace(day=1, hour=0, minute=0, second=0)
    return trial_status(
        account,
        project_count=await count_projects_for_account(account_id),
        scans_today=await count_usage_events(account_id, "scan", start_day),
        reports_this_month=await count_usage_events(account_id, "report", start_month),
    )


async def check_project_quota(account_id: int) -> tuple[bool, dict]:
    usage = await get_usage_status(account_id)
    limit = int(usage["projects"]["limit"] or 0)
    ok = limit <= 0 or int(usage["projects"]["used"]) < limit
    return ok, usage


async def check_daily_scan_quota(account_id: int) -> tuple[bool, dict]:
    usage = await get_usage_status(account_id)
    limit = int(usage["daily_scans"]["limit"] or 0)
    ok = limit <= 0 or int(usage["daily_scans"]["used"]) < limit
    return ok, usage


async def check_monthly_report_quota(account_id: int) -> tuple[bool, dict]:
    usage = await get_usage_status(account_id)
    limit = int(usage["monthly_reports"]["limit"] or 0)
    ok = limit <= 0 or int(usage["monthly_reports"]["used"]) < limit
    return ok, usage


async def record_usage_event(
    account_id: int,
    event_type: str,
    *,
    user_id: int | None = None,
    project_id: int | None = None,
    metadata: dict | None = None,
) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO usage_events (account_id, user_id, project_id, event_type, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (account_id, user_id, project_id, event_type, json.dumps(metadata or {})),
        )
        await db.commit()
        return int(cursor.lastrowid)
    finally:
        await db.close()


async def get_admin_summary() -> dict:
    db = await get_db()
    try:
        today = _sqlite_ts(_utc_now().replace(hour=0, minute=0, second=0))
        month = _sqlite_ts(_utc_now().replace(day=1, hour=0, minute=0, second=0))
        day_ago = _sqlite_ts(_utc_now() - timedelta(hours=24))

        async def scalar(sql: str, params: tuple = ()) -> int:
            cursor = await db.execute(sql, params)
            row = await cursor.fetchone()
            return int(row[0] or 0)

        summary = {
            "total_users": await scalar("SELECT COUNT(*) FROM users"),
            "new_users_today": await scalar("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today,)),
            "active_trial_accounts": await scalar(
                "SELECT COUNT(*) FROM accounts WHERE status = 'active' AND plan = 'free_trial' AND trial_ends_at >= datetime('now')"
            ),
            "expired_trial_accounts": await scalar(
                "SELECT COUNT(*) FROM accounts WHERE plan = 'free_trial' AND trial_ends_at < datetime('now')"
            ),
            "total_projects": await scalar("SELECT COUNT(*) FROM projects"),
            "projects_created_today": await scalar("SELECT COUNT(*) FROM projects WHERE created_at >= ?", (today,)),
            "scans_today": await scalar(
                "SELECT COUNT(*) FROM usage_events WHERE event_type = 'scan' AND created_at >= ?", (today,)
            ),
            "reports_this_month": await scalar(
                "SELECT COUNT(*) FROM usage_events WHERE event_type = 'report' AND created_at >= ?", (month,)
            ),
            "failed_tasks_24h": await scalar(
                "SELECT COUNT(*) FROM background_tasks WHERE status = 'failed' AND updated_at >= ?", (day_ago,)
            ),
        }

        cursor = await db.execute(
            """SELECT a.id, a.name, a.status, a.plan, COUNT(e.id) AS usage_count
               FROM accounts a
               LEFT JOIN usage_events e ON e.account_id = a.id AND e.created_at >= ?
               GROUP BY a.id
               ORDER BY usage_count DESC, a.id DESC
               LIMIT 10""",
            (day_ago,),
        )
        summary["high_usage_accounts"] = [
            {"id": row[0], "name": row[1], "status": row[2], "plan": row[3], "usage_count": row[4]}
            for row in await cursor.fetchall()
        ]

        cursor = await db.execute(
            """SELECT id, email, name, role, status, created_at, last_login_at
               FROM users ORDER BY created_at DESC, id DESC LIMIT 10"""
        )
        summary["recent_users"] = [_user_from_row(row) for row in await cursor.fetchall()]

        cursor = await db.execute(
            """SELECT id, name, plan, status, trial_started_at, trial_ends_at,
                      max_projects, daily_scan_limit, monthly_report_limit, created_at
               FROM accounts ORDER BY created_at DESC, id DESC LIMIT 10"""
        )
        summary["recent_accounts"] = [_account_from_row(row) for row in await cursor.fetchall()]

        cursor = await db.execute(
            """SELECT task_id, kind, project_id, status, error_json, created_at, updated_at
               FROM background_tasks
               WHERE status = 'failed'
               ORDER BY updated_at DESC
               LIMIT 10"""
        )
        summary["recent_failed_tasks"] = [
            {
                "task_id": row[0],
                "kind": row[1],
                "project_id": row[2],
                "status": row[3],
                "error": json.loads(row[4] or "{}"),
                "created_at": row[5],
                "updated_at": row[6],
            }
            for row in await cursor.fetchall()
        ]
        return summary
    finally:
        await db.close()


async def set_account_status(account_id: int, status: str) -> bool:
    if status not in {"active", "disabled"}:
        raise ValueError("invalid_status")
    db = await get_db()
    try:
        cursor = await db.execute("UPDATE accounts SET status = ? WHERE id = ?", (status, account_id))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def extend_account_trial(account_id: int, days: int) -> bool:
    days = max(1, min(days, 365))
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE accounts SET trial_ends_at = datetime(trial_ends_at, ?) WHERE id = ?",
            (f"+{days} days", account_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def update_account_quota(
    account_id: int,
    *,
    max_projects: int | None = None,
    daily_scan_limit: int | None = None,
    monthly_report_limit: int | None = None,
) -> bool:
    fields: list[str] = []
    values: list[int] = []
    for column, value in (
        ("max_projects", max_projects),
        ("daily_scan_limit", daily_scan_limit),
        ("monthly_report_limit", monthly_report_limit),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            values.append(max(0, int(value)))
    if not fields:
        return True
    values.append(account_id)
    db = await get_db()
    try:
        cursor = await db.execute(f"UPDATE accounts SET {', '.join(fields)} WHERE id = ?", tuple(values))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
