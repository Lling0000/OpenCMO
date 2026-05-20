"""Multi-tenant per-account settings tests.

Covers:
- account_settings rows are isolated between accounts (A cannot read B).
- llm.get_key resolves to the per-account snapshot bound by the middleware.
- Verification emails always use the system SMTP fallback (system=True).
- Legacy ``settings`` table rows survive and are still reachable via
  ``get_system_setting``.
- The boot-time backfill copies legacy global rows into account_settings under
  the admin account.
- POST /api/v1/settings writes onto the active account (no admin gate) and a
  second account's GET returns empty for that key.
- Saving non-admin account values does NOT pollute os.environ.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from opencmo import llm, storage

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from opencmo.web.app import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_account(*, email: str, name: str, role: str = "user") -> tuple[int, int]:
    """Create a (user, account) pair directly in the DB and return their ids."""

    async def _do() -> tuple[int, int]:
        await storage.ensure_db()
        db = await storage._db.get_db()
        try:
            cursor = await db.execute(
                """INSERT INTO users (email, password_hash, name, role, status, email_verified_at)
                   VALUES (?, '!seed', ?, ?, 'active', datetime('now'))""",
                (email, name, role),
            )
            user_id = int(cursor.lastrowid)
            trial_end = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            cursor = await db.execute(
                """INSERT INTO accounts (name, plan, status, trial_ends_at)
                   VALUES (?, 'free_trial', 'active', ?)""",
                (name, trial_end),
            )
            account_id = int(cursor.lastrowid)
            await db.execute(
                "INSERT INTO account_members (account_id, user_id, role) VALUES (?, ?, 'owner')",
                (account_id, user_id),
            )
            await db.commit()
            return user_id, account_id
        finally:
            await db.close()

    return asyncio.run(_do())


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Fresh SQLite DB per test plus clean module-level state."""
    monkeypatch.setenv("OPENCMO_ADMIN_EMAIL", "admin@example.test")
    for key in (
        "OPENCMO_SMTP_HOST",
        "OPENCMO_SMTP_USER",
        "OPENCMO_SMTP_PASS",
        "OPENCMO_SMTP_PORT",
        "OPENCMO_SMTP_FROM",
        "OPENCMO_SMTP_FROM_NAME",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    db_path = tmp_path / "settings_mt.db"
    with patch.object(storage, "_DB_PATH", db_path):
        # Force admin account creation by booting the schema once.
        asyncio.run(storage.ensure_db())
        yield db_path


# ---------------------------------------------------------------------------
# Storage-layer isolation
# ---------------------------------------------------------------------------


def test_account_settings_are_isolated_across_accounts(isolated_db):
    _, account_a = _seed_account(email="alice@example.test", name="Alice")
    _, account_b = _seed_account(email="bob@example.test", name="Bob")

    asyncio.run(storage.set_account_setting(account_a, "REDDIT_USERNAME", "alice_reddit"))

    assert asyncio.run(storage.get_account_setting(account_a, "REDDIT_USERNAME")) == "alice_reddit"
    assert asyncio.run(storage.get_account_setting(account_b, "REDDIT_USERNAME")) is None

    listing_a = asyncio.run(storage.list_account_settings(account_a))
    listing_b = asyncio.run(storage.list_account_settings(account_b))
    assert listing_a == {"REDDIT_USERNAME": "alice_reddit"}
    assert listing_b == {}


def test_account_settings_upsert_updates_existing_row(isolated_db):
    _, account_id = _seed_account(email="carol@example.test", name="Carol")

    asyncio.run(storage.set_account_setting(account_id, "REDDIT_USERNAME", "carol_v1"))
    asyncio.run(storage.set_account_setting(account_id, "REDDIT_USERNAME", "carol_v2"))

    assert asyncio.run(storage.get_account_setting(account_id, "REDDIT_USERNAME")) == "carol_v2"


def test_delete_account_setting_returns_true_when_row_existed(isolated_db):
    _, account_id = _seed_account(email="dave@example.test", name="Dave")
    asyncio.run(storage.set_account_setting(account_id, "FOO", "bar"))

    assert asyncio.run(storage.delete_account_setting(account_id, "FOO")) is True
    assert asyncio.run(storage.delete_account_setting(account_id, "FOO")) is False
    assert asyncio.run(storage.get_account_setting(account_id, "FOO")) is None


# ---------------------------------------------------------------------------
# get_key + ContextVar
# ---------------------------------------------------------------------------


def test_get_key_reads_account_snapshot_set_by_middleware(isolated_db):
    _, account_a = _seed_account(email="alice2@example.test", name="Alice2")
    _, account_b = _seed_account(email="bob2@example.test", name="Bob2")

    asyncio.run(storage.set_account_setting(account_a, "REDDIT_USERNAME", "alice_reddit"))

    snap_a = asyncio.run(storage.list_account_settings(account_a))
    snap_b = asyncio.run(storage.list_account_settings(account_b))

    # Bind A's snapshot — sync get_key sees alice's value.
    acct_token = llm.set_current_account_id(account_a)
    snap_token = llm.set_current_account_settings(snap_a)
    try:
        assert llm.get_key("REDDIT_USERNAME") == "alice_reddit"
    finally:
        llm.reset_current_account_settings(snap_token)
        llm.reset_current_account_id(acct_token)

    # Bind B's snapshot — must not see alice's value.
    acct_token = llm.set_current_account_id(account_b)
    snap_token = llm.set_current_account_settings(snap_b)
    try:
        assert llm.get_key("REDDIT_USERNAME") is None
    finally:
        llm.reset_current_account_settings(snap_token)
        llm.reset_current_account_id(acct_token)


def test_get_key_async_reads_per_account_via_db_when_snapshot_empty(isolated_db):
    _, account_a = _seed_account(email="alice3@example.test", name="Alice3")
    asyncio.run(storage.set_account_setting(account_a, "REDDIT_USERNAME", "alice_db_only"))

    # No snapshot bound — async path must still hit account_settings via DB.
    acct_token = llm.set_current_account_id(account_a)
    try:
        value = asyncio.run(llm.get_key_async("REDDIT_USERNAME"))
    finally:
        llm.reset_current_account_id(acct_token)
    assert value == "alice_db_only"


def test_publish_credentials_do_not_fallback_to_env_or_system(isolated_db, monkeypatch):
    """Tenant-missing publish creds must not resolve from global/system fallbacks."""
    admin_id = asyncio.run(storage.get_admin_account_id())
    _, tenant_account = _seed_account(email="tenant@example.test", name="Tenant")
    asyncio.run(storage.set_account_setting(admin_id, "REDDIT_CLIENT_ID", "admin-cid"))
    monkeypatch.setenv("REDDIT_CLIENT_ID", "env-cid")

    acct_token = llm.set_current_account_id(tenant_account)
    snap_token = llm.set_current_account_settings({})
    try:
        assert asyncio.run(llm.get_key_async("REDDIT_CLIENT_ID")) is None
        assert llm.get_key("REDDIT_CLIENT_ID") is None
    finally:
        llm.reset_current_account_settings(snap_token)
        llm.reset_current_account_id(acct_token)


# ---------------------------------------------------------------------------
# System fallback / legacy table
# ---------------------------------------------------------------------------


def test_legacy_settings_table_still_readable_via_get_system_setting(isolated_db):
    # Write directly into the legacy global table (mimics pre-v24 state).
    asyncio.run(storage.set_setting("LEGACY_ONLY_KEY", "legacy-value"))

    # No admin account has a row for this key, so the system fallback reads the
    # legacy table.
    assert asyncio.run(storage.get_system_setting("LEGACY_ONLY_KEY")) == "legacy-value"
    # The backward-compatible shim resolves the same way.
    assert asyncio.run(storage.get_setting("LEGACY_ONLY_KEY")) == "legacy-value"


def test_get_system_setting_prefers_admin_account_over_legacy_table(isolated_db):
    """When both rows exist, admin account wins."""
    admin_id = asyncio.run(storage.get_admin_account_id())
    asyncio.run(storage.set_account_setting(admin_id, "OVERLAP", "admin-wins"))
    asyncio.run(storage.set_setting("OVERLAP", "legacy-loses"))

    assert asyncio.run(storage.get_system_setting("OVERLAP")) == "admin-wins"


def test_backfill_copies_legacy_settings_into_admin_account_settings(tmp_path, monkeypatch):
    """The boot-time backfill must seed admin's account_settings from settings."""
    monkeypatch.setenv("OPENCMO_ADMIN_EMAIL", "admin@example.test")
    db_path = tmp_path / "backfill.db"
    with patch.object(storage, "_DB_PATH", db_path):
        # Bootstrap once to create schema + admin account.
        asyncio.run(storage.ensure_db())
        admin_id = asyncio.run(storage.get_admin_account_id())
        # Seed the legacy table after bootstrap.
        asyncio.run(storage.set_setting("PAGESPEED_API_KEY", "legacy-ps-key"))
        asyncio.run(storage.set_setting("DATAFORSEO_LOGIN", "legacy-login"))
        # Wipe any account_settings rows so the backfill fires again.

        async def _wipe() -> None:
            db = await storage._db.get_db()
            try:
                await db.execute("DELETE FROM account_settings")
                await db.commit()
            finally:
                await db.close()

        asyncio.run(_wipe())
        # Reset module cache so ensure_db re-runs the bootstrap hooks.
        storage._db._SCHEMA_READY_FOR = None
        asyncio.run(storage.ensure_db())

        listing = asyncio.run(storage.list_account_settings(admin_id))
        assert listing.get("PAGESPEED_API_KEY") == "legacy-ps-key"
        assert listing.get("DATAFORSEO_LOGIN") == "legacy-login"


# ---------------------------------------------------------------------------
# Verification email forces system SMTP
# ---------------------------------------------------------------------------


def test_verification_email_uses_system_smtp_when_account_has_no_creds(isolated_db):
    captured: dict = {}

    async def fake_send_mail(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"ok": True}

    with patch("opencmo.tools.email_verification.send_mail", side_effect=fake_send_mail):
        from opencmo.tools.email_verification import send_verification_code

        result = asyncio.run(send_verification_code("new@example.test", "123456", "en"))
        assert result["ok"] is True

    assert captured["kwargs"]["system"] is True


# ---------------------------------------------------------------------------
# Web router — per-account isolation through HTTP
# ---------------------------------------------------------------------------


def _set_session_account(monkeypatch, account_id: int, user_id: int) -> None:
    """Stub attach_request_context so a deterministic account is bound."""

    async def fake_attach(request):
        admin_email = os.environ.get("OPENCMO_ADMIN_EMAIL", "admin@example.test")
        admin_id_local = await storage.get_admin_account_id()
        is_admin = int(admin_id_local) == int(account_id)
        account_dict = {
            "id": account_id,
            "name": "Test Account",
            "plan": "free_trial",
            "status": "active",
            "trial_started_at": "",
            "trial_ends_at": "",
            "max_projects": 3,
            "daily_scan_limit": 3,
            "monthly_report_limit": 10,
            "created_at": "",
        }
        request.state.current_user = {"id": user_id, "email": admin_email}
        request.state.current_account = account_dict
        request.state.is_admin = is_admin
        return {"user": request.state.current_user, "account": account_dict, "is_admin": is_admin}

    monkeypatch.setattr("opencmo.web.app.attach_request_context", fake_attach)


def test_post_settings_writes_per_account_and_isolates_from_other_accounts(isolated_db, monkeypatch):
    user_a, account_a = _seed_account(email="acct_a@example.test", name="Acct A")
    user_b, account_b = _seed_account(email="acct_b@example.test", name="Acct B")

    # Account A saves a reddit credential.
    _set_session_account(monkeypatch, account_a, user_a)
    with TestClient(app) as client:
        resp = client.post("/api/v1/settings", json={"REDDIT_USERNAME": "alice_reddit"})
        assert resp.status_code == 200

    # Verify the row landed under account A only.
    assert asyncio.run(storage.get_account_setting(account_a, "REDDIT_USERNAME")) == "alice_reddit"
    assert asyncio.run(storage.get_account_setting(account_b, "REDDIT_USERNAME")) is None

    # Account B's GET must NOT surface alice's value.
    _set_session_account(monkeypatch, account_b, user_b)
    with TestClient(app) as client:
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["reddit_username"] == ""
        assert payload["reddit_configured"] is False

    # And a non-admin save must NOT pollute the process env.
    assert "REDDIT_USERNAME" not in os.environ


def test_post_settings_for_admin_account_does_sync_env(isolated_db, monkeypatch):
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)
    admin_id = asyncio.run(storage.get_admin_account_id())

    async def fake_get_user_by_admin() -> int:
        db = await storage._db.get_db()
        try:
            cursor = await db.execute(
                """SELECT u.id FROM users u
                   JOIN account_members m ON m.user_id = u.id
                   WHERE m.account_id = ? LIMIT 1""",
                (admin_id,),
            )
            row = await cursor.fetchone()
            return int(row[0])
        finally:
            await db.close()

    admin_user_id = asyncio.run(fake_get_user_by_admin())
    _set_session_account(monkeypatch, admin_id, admin_user_id)

    with TestClient(app) as client:
        resp = client.post("/api/v1/settings", json={"PAGESPEED_API_KEY": "admin-ps-key"})
        assert resp.status_code == 200

    assert os.environ.get("PAGESPEED_API_KEY") == "admin-ps-key"
    # And the per-account read returns the new value too.
    assert asyncio.run(storage.get_account_setting(admin_id, "PAGESPEED_API_KEY")) == "admin-ps-key"
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)


def test_get_settings_reports_system_smtp_active_when_admin_has_smtp(isolated_db, monkeypatch):
    """A non-admin account with no SMTP rows should surface system_smtp_active."""
    admin_id = asyncio.run(storage.get_admin_account_id())
    user_a, account_a = _seed_account(email="solo@example.test", name="Solo")

    asyncio.run(storage.set_account_setting(admin_id, "OPENCMO_SMTP_HOST", "mail.example.test"))
    asyncio.run(storage.set_account_setting(admin_id, "OPENCMO_SMTP_USER", "ops@example.test"))
    asyncio.run(storage.set_account_setting(admin_id, "OPENCMO_SMTP_PASS", "supersecret"))

    _set_session_account(monkeypatch, account_a, user_a)
    with TestClient(app) as client:
        payload = client.get("/api/v1/settings").json()
    assert payload["email_configured"] is False
    assert payload["system_smtp_active"] is True


def test_get_settings_for_account_with_own_smtp_does_not_show_system_active(isolated_db, monkeypatch):
    admin_id = asyncio.run(storage.get_admin_account_id())
    user_a, account_a = _seed_account(email="own_smtp@example.test", name="OwnSmtp")

    asyncio.run(storage.set_account_setting(admin_id, "OPENCMO_SMTP_HOST", "mail.example.test"))
    asyncio.run(storage.set_account_setting(admin_id, "OPENCMO_SMTP_USER", "ops@example.test"))
    asyncio.run(storage.set_account_setting(admin_id, "OPENCMO_SMTP_PASS", "supersecret"))

    asyncio.run(storage.set_account_setting(account_a, "OPENCMO_SMTP_HOST", "self.example.test"))
    asyncio.run(storage.set_account_setting(account_a, "OPENCMO_SMTP_USER", "me@example.test"))
    asyncio.run(storage.set_account_setting(account_a, "OPENCMO_SMTP_PASS", "self-secret"))

    _set_session_account(monkeypatch, account_a, user_a)
    with TestClient(app) as client:
        payload = client.get("/api/v1/settings").json()
    assert payload["email_configured"] is True
    assert payload["system_smtp_active"] is False


def test_session_middleware_binds_account_id_contextvar(isolated_db, monkeypatch):
    """When a session is active, llm.get_current_account_id() returns it inside the handler.

    Invokes ``session_context_middleware`` directly with a fake ``call_next``
    closure so we can observe what the downstream handler would see.
    """
    user_a, account_a = _seed_account(email="bound@example.test", name="Bound")
    asyncio.run(storage.set_account_setting(account_a, "REDDIT_USERNAME", "bound_alice"))

    _set_session_account(monkeypatch, account_a, user_a)

    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from opencmo.web.app import session_context_middleware

    captured: dict = {}

    async def fake_call_next(_request: Request):
        captured["account_id"] = llm.get_current_account_id()
        captured["reddit"] = llm.get_key("REDDIT_USERNAME")
        return JSONResponse({"ok": True})

    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": [],
    })
    response = asyncio.run(session_context_middleware(request, fake_call_next))
    assert response.status_code == 200

    assert captured["account_id"] == account_a
    assert captured["reddit"] == "bound_alice"
    # ContextVar must be reset once the middleware returns.
    assert llm.get_current_account_id() is None
