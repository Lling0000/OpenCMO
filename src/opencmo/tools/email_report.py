"""Email report — sends persisted AI CMO reports via the shared SMTP sender."""

from __future__ import annotations

import logging
import re
import uuid

from agents import function_tool

from opencmo.tools.email_send import send_mail

logger = logging.getLogger(__name__)
_REPORT_ASSET_RELATIVE_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=)(["\'])(/api/v1/report-assets/[a-f0-9]{32}\.svg)(\2)', re.IGNORECASE)


def _get_report_recipient() -> str | None:
    from opencmo import llm

    recipient = llm.get_key("OPENCMO_REPORT_EMAIL") or llm.get_key("OPENCMO_SMTP_USER")
    return str(recipient).strip() if recipient else None


def _get_smtp_config() -> dict | None:
    """Backward-compatible accessor for SMTP + recipient bundled together.

    Returns ``None`` when SMTP credentials *or* the report recipient are
    missing, so legacy callers that pre-checked this dict still get the same
    short-circuit behaviour.
    """
    from opencmo.tools.email_send import _smtp_config

    base = _smtp_config()
    if base is None:
        return None
    recipient = _get_report_recipient()
    if not recipient:
        return None
    return {
        "host": base["host"],
        "port": base["port"],
        "user": base["user"],
        "password": base["password"],
        "recipient": recipient,
    }


def _get_report_public_base_url() -> str:
    from opencmo import llm

    base_url = (
        llm.get_key("OPENCMO_PUBLIC_BASE_URL")
        or llm.get_key("OPENCMO_APP_BASE_URL")
        or llm.get_key("OPENCMO_REPORT_BASE_URL")
        or "https://www.aidcmo.com"
    )
    return str(base_url).rstrip("/")


def _make_report_asset_urls_absolute(html: str) -> str:
    base_url = _get_report_public_base_url()

    def replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{base_url}{match.group(3)}{match.group(4)}"

    return _REPORT_ASSET_RELATIVE_SRC_RE.sub(replace, html)


async def send_report_impl(project_id: int, *, locale: str = "zh", idempotency_key: str | None = None) -> dict:
    """Send each persisted report/recipient/locale/account once by default.

    A new nonempty idempotency_key explicitly requests a separate resend;
    retries must reuse that key. Uncertain SMTP outcomes are never retried
    automatically, including a claim left by a crashed or cancelled worker.
    """
    from opencmo import llm, storage
    from opencmo.storage.report_email_deliveries import claim_delivery, finish_delivery

    resend_key = (idempotency_key or "").strip()
    if len(resend_key) > 200:
        return {"ok": False, "error": "idempotency_key must be at most 200 characters"}

    locale = storage.normalize_report_locale(locale)
    recipient = _get_report_recipient()
    if not recipient:
        return {"ok": False, "error": "OPENCMO_REPORT_EMAIL not configured"}

    project = await storage.get_project(project_id, account_id=llm.get_current_account_id())
    if not project:
        return {"ok": False, "error": f"Project {project_id} not found"}

    report = await storage.get_latest_report(project_id, "periodic", "human", locale=locale)
    if not report:
        from opencmo.reports import generate_periodic_report_bundle

        generated = await generate_periodic_report_bundle(project_id, source_run_id=None, locale=locale)
        report = generated["human"]
    if report.get("generation_status") != "completed" or not (report.get("content_html") or report.get("content")):
        return {"ok": False, "error": "Latest weekly report is unavailable"}

    html = _make_report_asset_urls_absolute(report.get("content_html") or f"<pre>{report.get('content', '')}</pre>")
    subject = f"OpenCMO Weekly Brief: {project['brand_name']}"
    title_header = (
        report.get("content", "").splitlines()[0].lstrip("# ").strip()
        if report.get("content")
        else "Weekly Brief"
    ) or "Weekly Brief"

    response = {
        "ok": True,
        "recipient": recipient,
        "report_id": report["id"],
        "kind": report["kind"],
        "audience": report["audience"],
        "locale": report.get("locale", locale),
        "dev_mode": False,
    }

    # A simulated send must not suppress a future real delivery after SMTP is
    # configured. No SMTP operation occurs in this branch.
    if _get_smtp_config() is None:
        return {**response, "dev_mode": True, "delivery_state": "simulated"}

    claimed, delivery = await claim_delivery(
        account_id=project["account_id"], project_id=project_id,
        report_id=report["id"], recipient=recipient, locale=locale, resend_key=resend_key,
    )
    if not claimed:
        if delivery["status"] == "sent":
            return {**delivery["result"], "deduplicated": True}
        return {
            "ok": False, "error": "delivery_uncertain: previous send is in progress or may have been accepted; "
            "check delivery before explicitly resending with a new idempotency_key",
            "delivery_state": "uncertain", "retryable": False, "deduplicated": True,
            "report_id": report["id"],
        }

    try:
        result = await send_mail(
            recipient, subject, html,
            headers={"X-OpenCMO-Report-Title": title_header,
                     "Message-ID": f"<opencmo-report-delivery-{uuid.uuid4()}@aidcmo.com>"},
        )
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}

    if not result.get("ok") or result.get("dev_mode"):
        # The shared sender cannot distinguish a pre-DATA failure from SMTP
        # accepting DATA then losing its response. Prefer no duplicate send.
        response = {
            "ok": False, "error": f"delivery_uncertain: {result.get('error', 'SMTP configuration changed')}",
            "delivery_state": "uncertain", "retryable": False, "report_id": report["id"],
        }
        await finish_delivery(delivery["id"], status="uncertain", result=response)
        return response

    response["delivery_state"] = "sent"
    await finish_delivery(delivery["id"], status="sent", result=response)
    return response


@function_tool
async def send_email_report(project_id: int, idempotency_key: str | None = None) -> str:
    """Send an email report with latest scan data for a project.

    Args:
        project_id: The project ID to generate a report for.
        idempotency_key: Optional explicit resend operation key. Reuse the same
            key on retries; a new key sends another copy. Omit for normal sends.
    """
    result = await send_report_impl(project_id, idempotency_key=idempotency_key)
    if result["ok"]:
        if result.get("dev_mode"):
            return f"Report simulated for {result['recipient']}; SMTP not configured"
        if result.get("deduplicated"):
            return f"Report already sent to {result['recipient']} (duplicate send skipped)"
        return f"Report sent to {result['recipient']}"
    else:
        return f"Failed to send report: {result['error']}"
