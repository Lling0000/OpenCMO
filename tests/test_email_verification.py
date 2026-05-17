"""End-to-end email verification flow tests.

Covers:
- Signup issues a code without setting a session cookie.
- Wrong code attempts increment counters and lock at 5.
- Resend cooldown returns 429 with retry_after_seconds.
- Successful verify signs the user in (session cookie + /auth/me works).
- Login of unverified user returns 403 email_not_verified.
- Login of verified user works normally.
- Pre-existing (legacy) users keep working via the boot-time backfill.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from unittest.mock import patch

import pytest

from opencmo import storage

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import opencmo.web.app as web_app
from opencmo.web.app import app


_CAPTURED_CODES: list[dict] = []


def _fake_send_mail(to: str, subject: str, html: str, text: str | None = None) -> dict:
    """Synchronous-friendly capture that records what would have been sent.

    The real ``send_mail`` is async; we wrap this in an ``AsyncMock``-like
    coroutine when monkeypatching ``email_send.send_mail``.
    """
    # Extract the 6-digit code from the text body (or from html as fallback).
    import re

    haystack = text or html
    match = re.search(r"\b(\d{6})\b", haystack)
    code = match.group(1) if match else ""
    _CAPTURED_CODES.append({"to": to, "subject": subject, "code": code})
    return {"ok": True}


@pytest.fixture
def verification_db(tmp_path, monkeypatch):
    """Isolated DB + captured outbound mail for each test."""
    monkeypatch.setenv("OPENCMO_REQUIRE_SESSION_AUTH", "1")
    monkeypatch.setenv("OPENCMO_COOKIE_SECRET", "test-cookie-secret")
    monkeypatch.setenv("OPENCMO_SIGNUP_MODE", "open")
    monkeypatch.setenv("OPENCMO_ADMIN_EMAIL", "admin@example.test")
    db_path = tmp_path / "verify.db"
    web_app._AUTH_RATE_BUCKETS.clear()
    _CAPTURED_CODES.clear()

    async def _async_capture(to: str, subject: str, html: str, text: str | None = None) -> dict:
        return _fake_send_mail(to, subject, html, text)

    with patch.object(storage, "_DB_PATH", db_path), \
         patch("opencmo.tools.email_send.send_mail", side_effect=_async_capture), \
         patch("opencmo.tools.email_verification.send_mail", side_effect=_async_capture):
        yield
    web_app._AUTH_RATE_BUCKETS.clear()
    _CAPTURED_CODES.clear()


def _last_code_for(email: str) -> str:
    for entry in reversed(_CAPTURED_CODES):
        if entry["to"] == email:
            return entry["code"]
    raise AssertionError(f"no captured code for {email}")


def _signup(client: TestClient, email: str, password: str = "password123") -> dict:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "name": email.split("@", 1)[0]},
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["needs_verification"] is True
    return payload


def test_signup_returns_needs_verification_without_session(verification_db):
    with TestClient(app) as client:
        signup = _signup(client, "newcomer@example.test")
        assert "opencmo_session" not in client.cookies
        assert signup["email"] == "newcomer@example.test"
        assert signup["user_id"] > 0

        # /auth/me must report unauthenticated.
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["authenticated"] is False

        # A pending code exists for this user.
        user_id = signup["user_id"]
        pending = asyncio.run(storage.last_verification_send_at(user_id, "signup"))
        assert pending is not None
        assert _last_code_for("newcomer@example.test")


def test_wrong_code_increments_attempts_then_locks(verification_db):
    with TestClient(app) as client:
        signup = _signup(client, "lock@example.test")
        user_id = signup["user_id"]

        # 4 wrong attempts should each report remaining_attempts > 0.
        for expected_remaining in (4, 3, 2, 1):
            resp = client.post(
                "/api/v1/auth/verify-email",
                json={"user_id": user_id, "code": "999999"},
            )
            assert resp.status_code == 400, resp.text
            body = resp.json()
            assert body["error"] == "code_invalid"
            assert body["remaining_attempts"] == expected_remaining

        # 5th wrong attempt locks the code.
        resp = client.post(
            "/api/v1/auth/verify-email",
            json={"user_id": user_id, "code": "999999"},
        )
        assert resp.status_code == 429, resp.text
        assert resp.json()["error"] == "code_locked"


def test_resend_cooldown_blocks_within_60_seconds(verification_db):
    with TestClient(app) as client:
        signup = _signup(client, "cooldown@example.test")
        user_id = signup["user_id"]

        immediate = client.post("/api/v1/auth/resend-code", json={"user_id": user_id})
        assert immediate.status_code == 429
        body = immediate.json()
        assert body["error"] == "resend_cooldown"
        assert body["retry_after_seconds"] >= 1
        assert int(immediate.headers.get("Retry-After", "0")) >= 1


def test_verify_with_correct_code_signs_user_in(verification_db):
    with TestClient(app) as client:
        signup = _signup(client, "ok@example.test")
        user_id = signup["user_id"]
        code = _last_code_for("ok@example.test")
        assert len(code) == 6

        resp = client.post(
            "/api/v1/auth/verify-email",
            json={"user_id": user_id, "code": code},
        )
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["authenticated"] is True
        assert payload["user"]["email"] == "ok@example.test"
        assert "opencmo_session" in client.cookies

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "ok@example.test"


def test_unverified_user_login_returns_403_email_not_verified(verification_db):
    with TestClient(app) as client:
        signup = _signup(client, "unverified@example.test")
        user_id = signup["user_id"]

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "unverified@example.test", "password": "password123"},
        )
        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert body["error"] == "email_not_verified"
        assert body["user_id"] == user_id
        assert body["email"] == "unverified@example.test"


def test_verified_user_login_succeeds(verification_db):
    with TestClient(app) as client:
        signup = _signup(client, "verified@example.test")
        user_id = signup["user_id"]
        code = _last_code_for("verified@example.test")

        verify = client.post(
            "/api/v1/auth/verify-email",
            json={"user_id": user_id, "code": code},
        )
        assert verify.status_code == 200
        client.post("/api/v1/auth/logout")
        client.cookies.clear()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "verified@example.test", "password": "password123"},
        )
        assert login.status_code == 200, login.text
        assert login.json()["authenticated"] is True


def test_existing_legacy_users_remain_verified_after_backfill(tmp_path, monkeypatch):
    """A user created before this feature should keep working — backfill runs
    once at ensure_db() startup."""
    monkeypatch.setenv("OPENCMO_REQUIRE_SESSION_AUTH", "1")
    monkeypatch.setenv("OPENCMO_COOKIE_SECRET", "test-cookie-secret")
    monkeypatch.setenv("OPENCMO_SIGNUP_MODE", "open")
    monkeypatch.setenv("OPENCMO_ADMIN_EMAIL", "admin@example.test")

    db_path = tmp_path / "legacy.db"
    # Hand-craft a pre-feature schema with one existing user + matching
    # account but no email_verified_at column. The boot path must add the
    # column and backfill the timestamp so the legacy user can still log in.
    from opencmo.storage.accounts import hash_password

    with sqlite3.connect(db_path) as raw:
        raw.executescript(
            """
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version (version) VALUES (22);
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_login_at TEXT
            );
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free_trial',
                status TEXT NOT NULL DEFAULT 'active',
                trial_started_at TEXT NOT NULL DEFAULT (datetime('now')),
                trial_ends_at TEXT NOT NULL,
                max_projects INTEGER NOT NULL DEFAULT 3,
                daily_scan_limit INTEGER NOT NULL DEFAULT 3,
                monthly_report_limit INTEGER NOT NULL DEFAULT 10,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE account_members (
                account_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (account_id, user_id)
            );
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                user_id INTEGER,
                project_id INTEGER,
                event_type TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                input_items TEXT NOT NULL DEFAULT '[]',
                project_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL,
                aliases TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(brand_name, url)
            );
            """
        )
        raw.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            ("legacy@example.test", hash_password("password123"), "Legacy"),
        )
        raw.execute(
            "INSERT INTO accounts (name, trial_ends_at) VALUES (?, datetime('now', '+14 days'))",
            ("Legacy Account",),
        )
        raw.execute(
            "INSERT INTO account_members (account_id, user_id, role) VALUES (1, 1, 'owner')"
        )
        raw.commit()

    web_app._AUTH_RATE_BUCKETS.clear()

    async def _noop_send(to: str, subject: str, html: str, text: str | None = None) -> dict:
        return {"ok": True}

    with patch.object(storage, "_DB_PATH", db_path), \
         patch.object(storage, "_SCHEMA_READY_FOR", None), \
         patch("opencmo.tools.email_send.send_mail", side_effect=_noop_send), \
         patch("opencmo.tools.email_verification.send_mail", side_effect=_noop_send):
        with TestClient(app) as client:
            # The legacy user should now be verified and able to log in
            # without going through the verify-email flow.
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "legacy@example.test", "password": "password123"},
            )
            assert login.status_code == 200, login.text
            assert login.json()["authenticated"] is True

    web_app._AUTH_RATE_BUCKETS.clear()


def test_resend_after_cooldown_creates_new_code(verification_db, monkeypatch):
    """Override the cooldown to 0 so the resend goes through, and confirm the
    new code supersedes the old one."""
    with TestClient(app) as client:
        signup = _signup(client, "resend@example.test")
        user_id = signup["user_id"]
        first_code = _last_code_for("resend@example.test")

        # Bypass the 60s cooldown by patching the constant for this call.
        from opencmo.storage import verifications as ver_mod

        monkeypatch.setattr(ver_mod, "DEFAULT_RESEND_COOLDOWN_SECONDS", 0)
        # storage __init__ re-exports the value — also patch the alias.
        monkeypatch.setattr(storage, "DEFAULT_RESEND_COOLDOWN_SECONDS", 0)

        resend = client.post("/api/v1/auth/resend-code", json={"user_id": user_id})
        assert resend.status_code == 200, resend.text

        new_code = _last_code_for("resend@example.test")
        assert new_code != first_code

        # Old code should fail with no_pending_code (previous code was
        # marked consumed when the new one was issued).
        old_attempt = client.post(
            "/api/v1/auth/verify-email",
            json={"user_id": user_id, "code": first_code},
        )
        assert old_attempt.status_code in (400, 429)
        assert old_attempt.json()["error"] in {"code_invalid", "no_pending_code"}

        # New code must work.
        good = client.post(
            "/api/v1/auth/verify-email",
            json={"user_id": user_id, "code": new_code},
        )
        assert good.status_code == 200, good.text
        assert good.json()["authenticated"] is True


def test_storage_helpers_directly(verification_db):
    """Quick sanity coverage for the storage layer in isolation."""

    async def run() -> None:
        user, _account = await storage.create_user_with_account(
            "direct@example.test", "password123", "Direct"
        )
        code = await storage.create_verification_code(user["id"])
        assert code.isdigit() and len(code) == 6

        wrong = await storage.consume_verification_code(user["id"], "000000")
        assert wrong["ok"] is False
        assert wrong["error"] == "code_invalid"
        assert wrong["remaining_attempts"] == 4

        good = await storage.consume_verification_code(user["id"], code)
        assert good["ok"] is True

        # Re-consuming the same code is a no-op (no pending code).
        again = await storage.consume_verification_code(user["id"], code)
        assert again["ok"] is False
        assert again["error"] == "no_pending_code"

    asyncio.run(run())


# Touch ``time`` so an unused-import warning never fails a strict run.
assert callable(time.monotonic)
