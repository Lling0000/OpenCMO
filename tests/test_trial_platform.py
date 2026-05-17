"""Free-trial platform auth, isolation, quota, and admin tests."""

from __future__ import annotations

import asyncio
import sqlite3
from unittest.mock import patch

import pytest

from opencmo import storage

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import opencmo.web.app as web_app
from opencmo.web.app import app


_CAPTURED_VERIFICATION_CODES: list[dict] = []


async def _stub_send_mail(to: str, subject: str, html: str, text: str | None = None) -> dict:
    """Capture the 6-digit code so trial tests can complete signup via verify."""
    import re

    haystack = text or html
    match = re.search(r"\b(\d{6})\b", haystack)
    _CAPTURED_VERIFICATION_CODES.append({"to": to, "code": match.group(1) if match else ""})
    return {"ok": True}


@pytest.fixture
def trial_db(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCMO_REQUIRE_SESSION_AUTH", "1")
    monkeypatch.setenv("OPENCMO_COOKIE_SECRET", "test-cookie-secret")
    monkeypatch.setenv("OPENCMO_SIGNUP_MODE", "open")
    monkeypatch.setenv("OPENCMO_ADMIN_EMAIL", "admin@example.test")
    db_path = tmp_path / "trial.db"
    web_app._AUTH_RATE_BUCKETS.clear()
    _CAPTURED_VERIFICATION_CODES.clear()
    with patch.object(storage, "_DB_PATH", db_path), \
         patch("opencmo.tools.email_send.send_mail", side_effect=_stub_send_mail), \
         patch("opencmo.tools.email_verification.send_mail", side_effect=_stub_send_mail):
        yield
    web_app._AUTH_RATE_BUCKETS.clear()
    _CAPTURED_VERIFICATION_CODES.clear()


def _last_code_for(email: str) -> str:
    for entry in reversed(_CAPTURED_VERIFICATION_CODES):
        if entry["to"] == email and entry["code"]:
            return entry["code"]
    raise AssertionError(f"no captured code for {email}")


def _signup(client: TestClient, email: str, password: str = "password123") -> dict:
    """Sign up and immediately verify, returning the post-verify auth payload.

    This keeps the rest of the trial-platform suite working under the new
    signup -> verify-email flow without rewriting every test.
    """
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "name": email.split("@", 1)[0]},
    )
    assert resp.status_code == 201, resp.text
    signup_payload = resp.json()
    assert signup_payload.get("needs_verification") is True
    user_id = signup_payload["user_id"]
    code = _last_code_for(email)
    verify = client.post(
        "/api/v1/auth/verify-email",
        json={"user_id": user_id, "code": code},
    )
    assert verify.status_code == 200, verify.text
    payload = verify.json()
    assert payload["authenticated"] is True
    return payload


def test_signup_login_me_and_logout(trial_db):
    with TestClient(app) as client:
        signup = _signup(client, "user@example.test")
        assert signup["user"]["email"] == "user@example.test"
        assert signup["account"]["plan"] == "free_trial"
        assert "opencmo_session" in client.cookies

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "user@example.test"

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200
        assert client.get("/api/v1/auth/me").json()["authenticated"] is False

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.test", "password": "password123"},
        )
        assert login.status_code == 200
        assert login.json()["authenticated"] is True


def test_login_rate_limit_returns_429(trial_db, monkeypatch):
    monkeypatch.setenv("OPENCMO_LOGIN_RATE_LIMIT", "2")
    monkeypatch.setenv("OPENCMO_AUTH_RATE_WINDOW_SECONDS", "60")
    with TestClient(app) as client:
        _signup(client, "limited@example.test")
        client.post("/api/v1/auth/logout")

        for _ in range(2):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "limited@example.test", "password": "wrong-password"},
            )
            assert resp.status_code == 401

        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "limited@example.test", "password": "wrong-password"},
        )
        assert limited.status_code == 429
        assert limited.json()["error"] == "rate_limited"


def test_signup_rate_limit_returns_429(trial_db, monkeypatch):
    monkeypatch.setenv("OPENCMO_SIGNUP_RATE_LIMIT", "2")
    monkeypatch.setenv("OPENCMO_AUTH_RATE_WINDOW_SECONDS", "60")
    with TestClient(app) as client:
        for index in range(2):
            resp = client.post(
                "/api/v1/auth/signup",
                json={"email": f"signup-{index}@example.test", "password": "password123", "name": "Limited"},
            )
            assert resp.status_code == 201

        limited = client.post(
            "/api/v1/auth/signup",
            json={"email": "signup-3@example.test", "password": "password123", "name": "Limited"},
        )
        assert limited.status_code == 429
        assert limited.json()["error"] == "rate_limited"


def test_project_list_and_detail_are_account_isolated(trial_db):
    with TestClient(app) as client:
        account_a = _signup(client, "a@example.test")["account"]["id"]
        cookie_a = client.cookies.get("opencmo_session")
        _signup(client, "b@example.test")
        cookie_b = client.cookies.get("opencmo_session")

        project_id = asyncio.run(storage.ensure_project("Private A", "https://a.example.test", "testing", account_id=account_a))

        client.cookies.set("opencmo_session", cookie_a)
        projects_a = client.get("/api/v1/projects")
        assert projects_a.status_code == 200
        assert [item["id"] for item in projects_a.json()] == [project_id]

        client.cookies.set("opencmo_session", cookie_b)
        projects_b = client.get("/api/v1/projects")
        assert projects_b.status_code == 200
        assert projects_b.json() == []

        hidden = client.get(f"/api/v1/projects/{project_id}")
        assert hidden.status_code == 404
        assert client.get(f"/legacy/api/project/{project_id}/seo-data").status_code == 404

        client.cookies.clear()
        assert client.get("/api/v1/projects").status_code == 401


def test_chat_context_and_sessions_are_account_isolated(trial_db):
    with TestClient(app) as client:
        account_a = _signup(client, "chat-a@example.test")["account"]["id"]
        cookie_a = client.cookies.get("opencmo_session")
        project_a = asyncio.run(
            storage.ensure_project("Chat A", "https://chat-a.example.test", "testing", account_id=account_a)
        )
        created = client.post("/api/v1/chat/sessions", json={"project_id": project_a})
        assert created.status_code == 201
        session_id = created.json()["session_id"]
        assert [item["id"] for item in client.get("/api/v1/chat/sessions").json()] == [session_id]

        _signup(client, "chat-b@example.test")
        cookie_b = client.cookies.get("opencmo_session")
        client.cookies.set("opencmo_session", cookie_b)

        assert client.get(f"/api/v1/chat/context/{project_a}").status_code == 404
        assert client.post("/api/v1/chat/sessions", json={"project_id": project_a}).status_code == 404
        assert client.get("/api/v1/chat/sessions").json() == []
        assert client.get(f"/api/v1/chat/sessions/{session_id}/messages").status_code == 404
        assert client.post("/api/v1/chat", json={"session_id": session_id, "message": "hello"}).status_code == 404

        client.cookies.set("opencmo_session", cookie_a)
        assert [item["id"] for item in client.get("/api/v1/chat/sessions").json()] == [session_id]


def test_project_object_id_routes_are_account_isolated(trial_db):
    from opencmo.tools.performance_tracker import add_manual_tracking

    with TestClient(app) as client:
        account_a = _signup(client, "objects-a@example.test")["account"]["id"]
        cookie_a = client.cookies.get("opencmo_session")
        project_a = asyncio.run(
            storage.ensure_project("Objects A", "https://objects-a.example.test", "testing", account_id=account_a)
        )
        keyword_id = asyncio.run(storage.add_tracked_keyword(project_a, "owned keyword"))
        competitor_id = asyncio.run(storage.add_competitor(project_a, "Owned Competitor"))
        competitor_keyword_id = asyncio.run(storage.add_competitor_keyword(competitor_id, "owned competitor keyword"))
        campaign = asyncio.run(storage.create_campaign_run(project_a, "owned campaign", ["blog"]))
        draft = asyncio.run(storage.create_blog_draft(project_a, "task-owned", "launch", "en"))
        tracking_id = asyncio.run(
            add_manual_tracking(project_a, platform="other", url="https://example.test/post", title="Owned")
        )

        _signup(client, "objects-b@example.test")
        cookie_b = client.cookies.get("opencmo_session")
        client.cookies.set("opencmo_session", cookie_b)

        assert client.get(f"/api/v1/campaigns/{campaign['id']}").status_code == 404
        assert client.delete(f"/api/v1/keywords/{keyword_id}").status_code == 404
        assert client.get(f"/api/v1/competitors/{competitor_id}/keywords").status_code == 404
        assert client.post(f"/api/v1/competitors/{competitor_id}/keywords", json={"keyword": "leak"}).status_code == 404
        assert client.delete(f"/api/v1/competitors/{competitor_id}").status_code == 404
        assert client.delete(f"/api/v1/manual-tracking/{tracking_id}").status_code == 404
        assert client.get(f"/api/v1/blog/drafts/{draft['id']}").status_code == 404

        client.cookies.set("opencmo_session", cookie_a)
        assert client.get(f"/api/v1/campaigns/{campaign['id']}").status_code == 200
        assert client.get(f"/api/v1/competitors/{competitor_id}/keywords").status_code == 200
        assert client.get(f"/api/v1/blog/drafts/{draft['id']}").status_code == 200
        assert asyncio.run(storage.get_tracked_keyword(keyword_id)) is not None
        assert asyncio.run(storage.get_competitor(competitor_id)) is not None
        assert competitor_keyword_id > 0


def test_legacy_project_global_unique_is_reconciled(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCMO_REQUIRE_SESSION_AUTH", "1")
    monkeypatch.setenv("OPENCMO_COOKIE_SECRET", "test-cookie-secret")
    monkeypatch.setenv("OPENCMO_SIGNUP_MODE", "open")
    monkeypatch.setenv("OPENCMO_ADMIN_EMAIL", "admin@example.test")
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        db.execute("INSERT INTO schema_version (version) VALUES (20)")
        db.execute(
            """CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL,
                aliases TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(brand_name, url)
            )"""
        )
        db.commit()

    web_app._AUTH_RATE_BUCKETS.clear()
    _CAPTURED_VERIFICATION_CODES.clear()
    with patch.object(storage, "_DB_PATH", db_path), \
         patch.object(storage, "_SCHEMA_READY_FOR", None), \
         patch("opencmo.tools.email_send.send_mail", side_effect=_stub_send_mail), \
         patch("opencmo.tools.email_verification.send_mail", side_effect=_stub_send_mail):
        with TestClient(app) as client:
            account_a = _signup(client, "tenant-a@example.test")["account"]["id"]
            cookie_a = client.cookies.get("opencmo_session")
            account_b = _signup(client, "tenant-b@example.test")["account"]["id"]
            cookie_b = client.cookies.get("opencmo_session")

            project_a = asyncio.run(
                storage.ensure_project("Shared Site", "https://shared.example.test", "testing", account_id=account_a)
            )
            project_b = asyncio.run(
                storage.ensure_project("Shared Site", "https://shared.example.test", "testing", account_id=account_b)
            )

            assert project_a != project_b
            client.cookies.set("opencmo_session", cookie_a)
            assert [item["id"] for item in client.get("/api/v1/projects").json()] == [project_a]
            client.cookies.set("opencmo_session", cookie_b)
            assert [item["id"] for item in client.get("/api/v1/projects").json()] == [project_b]
    web_app._AUTH_RATE_BUCKETS.clear()


def test_admin_summary_requires_admin(trial_db):
    with TestClient(app) as client:
        _signup(client, "admin@example.test")
        admin_cookie = client.cookies.get("opencmo_session")
        _signup(client, "normal@example.test")
        user_cookie = client.cookies.get("opencmo_session")

        client.cookies.set("opencmo_session", user_cookie)
        denied = client.get("/api/v1/admin/summary")
        assert denied.status_code == 403

        client.cookies.set("opencmo_session", admin_cookie)
        summary = client.get("/api/v1/admin/summary")
        assert summary.status_code == 200
        data = summary.json()
        assert data["total_users"] >= 2
        assert "active_trial_accounts" in data


def test_admin_account_actions_update_and_disable_access(trial_db):
    with TestClient(app) as client:
        _signup(client, "admin@example.test")
        admin_cookie = client.cookies.get("opencmo_session")
        user_payload = _signup(client, "managed@example.test")
        user_cookie = client.cookies.get("opencmo_session")
        account_id = user_payload["account"]["id"]

        client.cookies.set("opencmo_session", admin_cookie)
        quota = client.post(
            f"/api/v1/admin/accounts/{account_id}/quota",
            json={"max_projects": 7, "daily_scan_limit": 8, "monthly_report_limit": 9},
        )
        assert quota.status_code == 200
        extended = client.post(f"/api/v1/admin/accounts/{account_id}/extend-trial", json={"days": 3})
        assert extended.status_code == 200
        disabled = client.post(f"/api/v1/admin/accounts/{account_id}/disable")
        assert disabled.status_code == 200

        account = asyncio.run(storage.get_account(account_id))
        assert account is not None
        assert account["status"] == "disabled"
        assert account["max_projects"] == 7
        assert account["daily_scan_limit"] == 8
        assert account["monthly_report_limit"] == 9

        client.cookies.set("opencmo_session", user_cookie)
        assert client.get("/api/v1/projects").status_code == 401


def test_project_quota_blocks_new_monitor_creation(trial_db, monkeypatch):
    monkeypatch.setenv("OPENCMO_FREE_MAX_PROJECTS", "1")
    with TestClient(app) as client:
        account_id = _signup(client, "quota@example.test")["account"]["id"]
        asyncio.run(storage.ensure_project("Existing", "https://existing.example.test", "testing", account_id=account_id))

        resp = client.post("/api/v1/monitors", json={"url": "https://second.example.test"})
        assert resp.status_code == 429
        assert resp.json()["error"] == "project_quota_exceeded"


def test_daily_scan_quota_blocks_monitor_creation(trial_db, monkeypatch):
    monkeypatch.setenv("OPENCMO_FREE_DAILY_SCANS", "1")
    with TestClient(app) as client:
        account_id = _signup(client, "daily-quota@example.test")["account"]["id"]
        awaitable = storage.record_usage_event(account_id, "scan", metadata={"source": "test"})
        asyncio.run(awaitable)

        resp = client.post("/api/v1/monitors", json={"url": "https://daily-quota.example.test"})
        assert resp.status_code == 429
        assert resp.json()["error"] == "daily_scan_quota_exceeded"


def test_monthly_report_quota_blocks_report_generation(trial_db, monkeypatch):
    monkeypatch.setenv("OPENCMO_FREE_MONTHLY_REPORTS", "1")
    with TestClient(app) as client:
        account_id = _signup(client, "report-quota@example.test")["account"]["id"]
        project_id = asyncio.run(
            storage.ensure_project("Report Quota", "https://report-quota.example.test", "testing", account_id=account_id)
        )
        asyncio.run(storage.record_usage_event(account_id, "report", project_id=project_id, metadata={"source": "test"}))

        resp = client.post(f"/api/v1/projects/{project_id}/reports/summary/regenerate")
        assert resp.status_code == 429
        assert resp.json()["error"] == "monthly_report_quota_exceeded"
