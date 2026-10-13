"""Tests for email report — SMTP config, HTML build, send logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


def test_smtp_config_missing(monkeypatch):
    """Missing SMTP vars → None."""
    from opencmo.tools.email_report import _get_smtp_config

    monkeypatch.delenv("OPENCMO_SMTP_HOST", raising=False)
    assert _get_smtp_config() is None


def test_smtp_config_partial(monkeypatch):
    """Partial SMTP vars → None."""
    from opencmo.tools.email_report import _get_smtp_config

    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("OPENCMO_SMTP_PORT", "587")
    monkeypatch.delenv("OPENCMO_SMTP_USER", raising=False)
    assert _get_smtp_config() is None


def test_smtp_config_complete(monkeypatch):
    """All SMTP vars → valid config dict."""
    from opencmo.tools.email_report import _get_smtp_config

    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("OPENCMO_SMTP_PORT", "587")
    monkeypatch.setenv("OPENCMO_SMTP_USER", "user@gmail.com")
    monkeypatch.setenv("OPENCMO_SMTP_PASS", "secret")
    monkeypatch.setenv("OPENCMO_REPORT_EMAIL", "report@example.com")

    config = _get_smtp_config()
    assert config is not None
    assert config["host"] == "smtp.gmail.com"
    assert config["port"] == 587
    assert config["recipient"] == "report@example.com"






@pytest.mark.asyncio
async def test_send_report_success(tmp_path, monkeypatch):
    """Successful SMTP send."""
    from opencmo import storage as _st
    monkeypatch.setattr(_st, "_DB_PATH", tmp_path / "test.db")
    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("OPENCMO_SMTP_PORT", "587")
    monkeypatch.setenv("OPENCMO_SMTP_USER", "user@test.com")
    monkeypatch.setenv("OPENCMO_SMTP_PASS", "pass")
    monkeypatch.setenv("OPENCMO_REPORT_EMAIL", "report@test.com")
    monkeypatch.setenv("OPENCMO_PUBLIC_BASE_URL", "https://reports.example.com")

    from opencmo import storage
    from opencmo.tools.email_report import send_report_impl

    pid = await storage.ensure_project("Test", "https://example.com", "saas")

    fake_report = {
        "id": 1, "kind": "periodic", "audience": "human",
        "generation_status": "completed",
        "content": "# Weekly Brief\nAll good.",
        "content_html": (
            "<h1>Weekly Brief</h1>"
            '<figure><img src="/api/v1/report-assets/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.svg" alt="Chart" /></figure>'
        ),
    }
    fake_bundle = {"human": fake_report, "agent": fake_report}

    with patch("smtplib.SMTP") as mock_smtp, \
         patch("opencmo.reports.generate_periodic_report_bundle", AsyncMock(return_value=fake_bundle)):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        result = await send_report_impl(pid)

    assert result["ok"]
    assert result["recipient"] == "report@test.com"
    sent_message = mock_server.send_message.call_args[0][0]
    sent_html = sent_message.get_payload()[0].get_payload(decode=True).decode()
    assert 'src="https://reports.example.com/api/v1/report-assets/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.svg"' in sent_html


@pytest.mark.asyncio
async def test_send_report_smtp_error(tmp_path, monkeypatch):
    """SMTP error returns error dict, doesn't raise."""
    from opencmo import storage as _st
    monkeypatch.setattr(_st, "_DB_PATH", tmp_path / "test.db")
    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("OPENCMO_SMTP_PORT", "587")
    monkeypatch.setenv("OPENCMO_SMTP_USER", "user@test.com")
    monkeypatch.setenv("OPENCMO_SMTP_PASS", "pass")
    monkeypatch.setenv("OPENCMO_REPORT_EMAIL", "report@test.com")

    from opencmo import storage
    from opencmo.tools.email_report import send_report_impl

    pid = await storage.ensure_project("Test", "https://example.com", "saas")

    fake_report = {
        "id": 1, "kind": "periodic", "audience": "human",
        "generation_status": "completed",
        "content": "# Weekly Brief\nAll good.",
        "content_html": "<h1>Weekly Brief</h1><p>All good.</p>",
    }
    fake_bundle = {"human": fake_report, "agent": fake_report}

    with patch("smtplib.SMTP", side_effect=Exception("Connection refused")), \
         patch("opencmo.reports.generate_periodic_report_bundle", AsyncMock(return_value=fake_bundle)):
        result = await send_report_impl(pid)

    assert not result["ok"]
    assert "Connection refused" in result["error"]


@pytest.mark.asyncio
async def test_maybe_send_cron_full_only(tmp_path, monkeypatch):
    """Only (full, cron) triggers email; (full, manual) and (seo, cron) don't."""
    from opencmo import storage as _st
    monkeypatch.setattr(_st, "_DB_PATH", tmp_path / "test.db")
    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("OPENCMO_SMTP_PORT", "587")
    monkeypatch.setenv("OPENCMO_SMTP_USER", "u")
    monkeypatch.setenv("OPENCMO_SMTP_PASS", "p")
    monkeypatch.setenv("OPENCMO_REPORT_EMAIL", "r@t.com")

    from opencmo.scheduler import _maybe_send_email_report

    with patch("opencmo.tools.email_report.send_report_impl", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"ok": True, "recipient": "r@t.com"}

        await _maybe_send_email_report(1, "full", "cron")
        assert mock_send.call_count == 1

        mock_send.reset_mock()
        await _maybe_send_email_report(1, "full", "manual")
        assert mock_send.call_count == 0

        await _maybe_send_email_report(1, "seo", "cron")
        assert mock_send.call_count == 0


@pytest_asyncio.fixture
async def delivery_context(tmp_path, monkeypatch):
    from opencmo import llm, storage

    monkeypatch.setattr(storage, "_DB_PATH", tmp_path / "delivery.db")
    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("OPENCMO_SMTP_USER", "user@test.com")
    monkeypatch.setenv("OPENCMO_SMTP_PASS", "pass")
    monkeypatch.setenv("OPENCMO_REPORT_EMAIL", "report@test.com")
    # Context keys make this fixture independent of process/account defaults.
    token = llm.set_request_keys({"OPENCMO_SMTP_PASS": "pass"})
    project_id = await storage.ensure_project("Delivery", "https://example.com", "saas")
    report = {"id": 100, "kind": "periodic", "audience": "human", "locale": "zh",
              "generation_status": "completed", "content": "# Weekly Brief", "content_html": "<h1>Brief</h1>"}
    monkeypatch.setattr(storage, "get_latest_report", AsyncMock(return_value=report))
    try:
        yield project_id, report
    finally:
        llm.reset_request_keys(token)


@pytest.mark.asyncio
async def test_delivery_retry_is_durable_and_schema_upgrade_is_idempotent(delivery_context, monkeypatch):
    from opencmo import storage
    from opencmo.tools import email_report

    pid, _ = delivery_context
    sender = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(email_report, "send_mail", sender)
    first = await email_report.send_report_impl(pid)
    # Simulate a fresh process boot against the same on-disk database twice.
    for _ in range(2):
        monkeypatch.setattr(storage, "_SCHEMA_READY_FOR", None)
        await storage.ensure_db()
    second = await email_report.send_report_impl(pid)
    assert first["ok"] and second["ok"] and second["deduplicated"]
    assert sender.await_count == 1


@pytest.mark.asyncio
async def test_concurrent_delivery_has_one_smtp_operation(delivery_context, monkeypatch):
    import asyncio

    from opencmo.tools import email_report

    pid, _ = delivery_context
    started, finish = asyncio.Event(), asyncio.Event()

    async def sender(*args, **kwargs):
        started.set()
        await finish.wait()
        return {"ok": True}

    mocked = AsyncMock(side_effect=sender)
    monkeypatch.setattr(email_report, "send_mail", mocked)
    task = asyncio.create_task(email_report.send_report_impl(pid))
    await started.wait()
    second = await email_report.send_report_impl(pid)
    assert not second["ok"] and not second["retryable"]
    finish.set()
    assert (await task)["ok"]
    assert mocked.await_count == 1


@pytest.mark.asyncio
async def test_failed_or_crashed_delivery_never_automatically_retries(delivery_context, monkeypatch):
    import asyncio

    from opencmo.tools import email_report

    pid, _ = delivery_context
    sender = AsyncMock(return_value={"ok": False, "error": "Disconnected after DATA"})
    monkeypatch.setattr(email_report, "send_mail", sender)
    first = await email_report.send_report_impl(pid)
    second = await email_report.send_report_impl(pid)
    assert first["delivery_state"] == second["delivery_state"] == "uncertain"
    assert not first["retryable"] and sender.await_count == 1

    sender.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await email_report.send_report_impl(pid, idempotency_key="cancelled-resend")
    sender.side_effect = None
    third = await email_report.send_report_impl(pid, idempotency_key="cancelled-resend")
    assert third["delivery_state"] == "uncertain" and sender.await_count == 2


@pytest.mark.asyncio
async def test_new_report_recipient_locale_and_explicit_resend_are_distinct(delivery_context, monkeypatch):
    from opencmo.tools import email_report

    pid, report = delivery_context
    sender = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(email_report, "send_mail", sender)
    assert (await email_report.send_report_impl(pid))["ok"]
    assert (await email_report.send_report_impl(pid, idempotency_key="resend-1"))["ok"]
    assert (await email_report.send_report_impl(pid, idempotency_key="resend-1"))["deduplicated"]
    report["id"] += 1
    assert (await email_report.send_report_impl(pid))["ok"]
    monkeypatch.setenv("OPENCMO_REPORT_EMAIL", "another@test.com")
    assert (await email_report.send_report_impl(pid))["ok"]
    report["locale"] = "en"
    assert (await email_report.send_report_impl(pid, locale="en"))["ok"]
    assert sender.await_count == 5


@pytest.mark.asyncio
async def test_dev_mode_does_not_claim_real_delivery(delivery_context, monkeypatch):
    from opencmo.tools import email_report

    pid, _ = delivery_context
    sender = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(email_report, "send_mail", sender)
    monkeypatch.delenv("OPENCMO_SMTP_HOST")
    assert (await email_report.send_report_impl(pid))["delivery_state"] == "simulated"
    sender.assert_not_awaited()
    monkeypatch.setenv("OPENCMO_SMTP_HOST", "smtp.test.com")
    assert (await email_report.send_report_impl(pid))["delivery_state"] == "sent"
    sender.assert_awaited_once()


@pytest.mark.asyncio
async def test_delivery_rejects_foreign_account(delivery_context, monkeypatch):
    from opencmo import llm, storage
    from opencmo.tools import email_report

    pid, _ = delivery_context
    project = await storage.get_project(pid)
    sender = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(email_report, "send_mail", sender)
    token = llm.set_current_account_id(project["account_id"] + 100)
    try:
        assert not (await email_report.send_report_impl(pid))["ok"]
        sender.assert_not_awaited()
    finally:
        llm.reset_current_account_id(token)
