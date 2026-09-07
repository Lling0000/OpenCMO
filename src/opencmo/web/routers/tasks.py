"""Tasks and scan runs API router."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from opencmo import storage
from opencmo.background import service as bg_service
from opencmo.opportunities import build_project_opportunity_snapshot
from opencmo.web.auth import get_request_account_id

router = APIRouter(prefix="/api/v1")

_SCAN_STAGE_ORDER = [
    "context_build",
    "signal_collect",
    "signal_normalize",
    "domain_review",
    "strategy_synthesis",
    "persist_publish",
]


async def _task_visible(task: dict, account_id: int) -> bool:
    if task.get("kind") == "knowledge":
        from opencmo.rag.store import one
        return await one("SELECT 1 FROM rag_task_owners WHERE task_id=? AND account_id=?", (task["task_id"], account_id)) is not None
    project_id = task.get("project_id")
    if project_id is None:
        return False
    return await storage.get_project(int(project_id), account_id=account_id) is not None


async def _scan_run_visible(task_id: str, account_id: int) -> bool:
    run = await storage.get_scan_run_by_task_id(task_id)
    if not run:
        return False
    return await storage.get_project(int(run["project_id"]), account_id=account_id) is not None


def _compat_status(status: str) -> str:
    if status in {"queued", "claimed"}:
        return "pending"
    if status == "cancel_requested":
        return "running"
    if status == "cancelled":
        return "failed"
    return status


def _progress_from_events(events: list[dict]) -> list[dict]:
    progress: list[dict] = []
    for event in events:
        if event["event_type"] != "progress":
            continue
        payload = event["payload"] or {}
        if payload:
            progress.append(payload)
            continue
        progress.append(
            {
                "stage": event["phase"],
                "status": event["status"],
                "summary": event["summary"],
            }
        )
    return progress


def _latest_progress_summary(events: list[dict]) -> str:
    for event in reversed(events):
        if event["event_type"] != "progress":
            continue
        payload = event["payload"] or {}
        summary = payload.get("summary") or payload.get("detail") or event["summary"] or ""
        if summary:
            return summary
    return ""


def _progress_payload(event: dict) -> dict:
    return event["payload"] or {}


def _event_stage(event: dict) -> str:
    payload = _progress_payload(event)
    return payload.get("stage") or event["phase"] or ""


def _event_status(event: dict) -> str:
    payload = _progress_payload(event)
    return payload.get("status") or event["status"] or ""


def _event_summary(event: dict) -> str:
    payload = _progress_payload(event)
    return payload.get("summary") or payload.get("detail") or event["summary"] or ""


def _watchout_from_event(event: dict) -> dict | None:
    if event["event_type"] != "progress":
        return None

    payload = _progress_payload(event)
    stage = _event_stage(event) or "unknown"
    status = _event_status(event)
    summary = _event_summary(event)
    text = summary.lower()
    code = payload.get("code")
    kind = payload.get("kind")
    hint = payload.get("hint")
    blocking = bool(payload.get("blocking", False))

    if not code and "no llm api key" in text:
        code = "no_llm_key"
        kind = "coverage_gap"
        hint = hint or "Add an AI provider key, then rerun the scan to unlock keyword extraction and competitor discovery."
        blocking = True
    elif not code and "did not extract any keywords" in text:
        code = "keywords_missing"
        kind = "coverage_gap"
        hint = hint or "Seed initial keywords or rerun after crawl access is fixed so downstream SEO and SERP checks have coverage."
        blocking = True
    elif not code and "recovered" in text and "page metadata" in text:
        code = "html_meta_fallback"
        kind = "fallback"
        hint = hint or "OpenCMO recovered metadata from the page title and meta tags because the rendered page body was not usable."
    elif not code and ("rate limit" in text or "429" in text):
        code = "provider_rate_limit"
        kind = "source_limit"
        hint = hint or "Retry after the provider limit resets, or add a dedicated provider key to reduce throttling."
    elif not code and "fallback" in text:
        code = "provider_fallback"
        kind = "fallback"
        hint = hint or "A backup source kept this stage moving, but coverage may be thinner than the primary path."
    elif status == "failed":
        code = code or "task_error"
        kind = kind or "task_error"
        hint = hint or "Retry the scan. If the issue persists, inspect provider configuration and network access."

    if not code or not kind:
        return None

    title_map = {
        "no_llm_key": "AI-assisted context extraction is unavailable",
        "keywords_missing": "Keyword coverage is missing",
        "html_meta_fallback": "Metadata fallback was used",
        "provider_rate_limit": "A source provider is rate limited",
        "provider_fallback": "A backup source was used",
        "task_error": "This stage ended with an error",
    }

    return {
        "stage": stage,
        "status": status or "warning",
        "kind": kind,
        "code": code,
        "title": title_map.get(code, "Stage coverage warning"),
        "summary": summary,
        "resolution": hint or _resolution_hint(summary),
        "blocking": blocking,
    }


def _scan_watchouts(events: list[dict], task_error: str | None = None) -> list[dict]:
    watchouts: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for event in events:
        watchout = _watchout_from_event(event)
        if watchout is None:
            continue
        key = (watchout["stage"], watchout["code"], watchout["summary"])
        if key in seen:
            continue
        seen.add(key)
        watchouts.append(watchout)

    if task_error:
        key = ("task", "task_error", task_error)
        if key not in seen:
            watchouts.append(
                {
                    "stage": "task",
                    "status": "failed",
                    "kind": "task_error",
                    "code": "task_error",
                    "title": "The scan did not finish cleanly",
                    "summary": task_error,
                    "resolution": _resolution_hint(task_error),
                    "blocking": True,
                }
            )

    return watchouts


def _latest_stage_cards(events: list[dict]) -> list[dict]:
    cards: dict[str, dict] = {}
    watchouts_by_stage: dict[str, list[dict]] = {}

    for event in events:
        watchout = _watchout_from_event(event)
        if watchout is not None:
            watchouts_by_stage.setdefault(watchout["stage"], []).append(watchout)

        if event["event_type"] != "progress":
            continue
        payload = _progress_payload(event)
        stage = _event_stage(event)
        if not stage:
            continue
        summary = _event_summary(event)
        cards[stage] = {
            "stage": stage,
            "status": payload.get("status") or event["status"] or "running",
            "summary": summary,
            "agent": payload.get("agent") or "",
            "event_count": cards.get(stage, {}).get("event_count", 0) + 1,
        }

    for stage, card in cards.items():
        stage_watchouts = watchouts_by_stage.get(stage, [])
        if any(item["blocking"] or item["kind"] in {"coverage_gap", "source_limit", "task_error"} for item in stage_watchouts):
            card["kind"] = "degraded"
        elif any(item["kind"] == "fallback" for item in stage_watchouts):
            card["kind"] = "fallback"
        else:
            card["kind"] = "normal"
        if stage_watchouts:
            card["hint"] = stage_watchouts[-1]["resolution"]

    return sorted(
        cards.values(),
        key=lambda item: (
            _SCAN_STAGE_ORDER.index(item["stage"])
            if item["stage"] in _SCAN_STAGE_ORDER
            else len(_SCAN_STAGE_ORDER),
            item["stage"],
        ),
    )


def _resolution_hint(summary: str) -> str:
    text = (summary or "").lower()
    if "api key" in text or "no llm" in text:
        return "Configure the missing provider keys, then rerun the scan for full analysis coverage."
    if "fallback" in text:
        return "Fallback coverage is usable, but review the source evidence before acting on it."
    if "rate limit" in text or "429" in text:
        return "Retry after the provider limit resets, or add a dedicated API key to reduce throttling."
    if "failed" in text or "error" in text:
        return "Retry the scan. If the issue persists, inspect provider configuration and network access."
    return "Review this stage before acting on the final recommendations."


def _scan_issues(events: list[dict], task_error: str | None = None) -> list[dict]:
    return [
        {
            "stage": item["stage"],
            "status": item["status"] if item["status"] in {"warning", "failed"} else "warning",
            "summary": item["summary"],
            "resolution": item["resolution"],
        }
        for item in _scan_watchouts(events, task_error)
        if item["status"] in {"warning", "failed"} or item["blocking"] or item["kind"] == "fallback"
    ]


def _scan_quality(task: dict, watchouts: list[dict]) -> dict:
    blocking_watchouts = [item for item in watchouts if item["blocking"]]
    fallback_titles: list[str] = []
    source_warnings: list[str] = []

    for item in watchouts:
        if item["kind"] == "fallback" and item["title"] not in fallback_titles:
            fallback_titles.append(item["title"])
        if item["kind"] in {"source_limit", "coverage_gap"} and item["title"] not in source_warnings:
            source_warnings.append(item["title"])

    if task["status"] == "failed" or blocking_watchouts:
        return {
            "level": "limited",
            "headline": "This run finished with important coverage gaps.",
            "summary": "Review the blocked or incomplete stages before acting on the full set of recommendations.",
            "blocking": True,
            "fallbacks_used": fallback_titles,
            "source_warnings": source_warnings,
        }
    if watchouts:
        return {
            "level": "partial",
            "headline": "This run is usable, but some sources were degraded.",
            "summary": "OpenCMO completed the scan with fallback paths or provider limits, so treat the output as directionally useful rather than fully complete.",
            "blocking": False,
            "fallbacks_used": fallback_titles,
            "source_warnings": source_warnings,
        }
    return {
        "level": "reliable",
        "headline": "This run has full baseline coverage.",
        "summary": "The core stages completed without known source gaps or fallback-only output.",
        "blocking": False,
        "fallbacks_used": [],
        "source_warnings": [],
    }


def _unique_domains(findings: list[dict], recommendations: list[dict], opportunities: list[dict] | None = None) -> list[str]:
    ordered: list[str] = []
    for item in findings + recommendations + (opportunities or []):
        domain = item.get("domain")
        if domain and domain not in ordered:
            ordered.append(domain)
    return ordered


def _overview_headline(task: dict, findings: list[dict], recommendations: list[dict]) -> str:
    if task["status"] == "failed":
        return (task["error"] or {}).get("message") or "Scan failed before a complete monitoring brief was created."
    if findings or recommendations:
        return (
            f"{len(findings)} findings and {len(recommendations)} "
            f"{'recommended action' if len(recommendations) == 1 else 'recommended actions'} ready."
        )
    return (task["result"] or {}).get("summary") or "Initial scan completed."


async def _serialize_scan_artifacts(task: dict) -> dict:
    events = await bg_service.list_task_events(task["task_id"])
    findings = await storage.get_task_findings(task["task_id"])
    recommendations = await storage.get_task_recommendations(task["task_id"])
    snapshot = await build_project_opportunity_snapshot(task["project_id"])
    opportunities = snapshot["opportunities"]
    error_message = (task["error"] or {}).get("message")
    watchouts = _scan_watchouts(events, error_message if task["status"] == "failed" else None)

    return {
        "overview": {
            "headline": _overview_headline(task, findings, recommendations),
            "findings_count": len(findings),
            "recommendations_count": len(recommendations),
            "focus_domains": _unique_domains(findings, recommendations, opportunities["top"]),
        },
        "quality": _scan_quality(task, watchouts),
        "stage_cards": _latest_stage_cards(events),
        "watchouts": watchouts,
        "issues": _scan_issues(events, error_message if task["status"] == "failed" else None),
        "brief": {
            "top_findings": findings[:3],
            "top_recommendations": recommendations[:3],
        },
        "opportunities": opportunities,
        "cluster_summary": snapshot["cluster_summary"],
    }


async def _serialize_scan_task(task: dict) -> dict:
    events = await bg_service.list_task_events(task["task_id"])
    payload = task["payload"]
    result = task["result"] or {}
    error = task["error"] or {}
    return {
        "task_id": task["task_id"],
        "task_kind": "scan",
        "monitor_id": payload["monitor_id"],
        "project_id": task["project_id"],
        "job_type": payload["job_type"],
        "status": _compat_status(task["status"]),
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
        "error": error.get("message"),
        "progress": _progress_from_events(events),
        "run_id": result.get("run_id"),
        "summary": result.get("summary") or error.get("message") or _latest_progress_summary(events),
        "findings_count": result.get("findings_count", 0),
        "recommendations_count": result.get("recommendations_count", 0),
    }


async def _serialize_report_task(task: dict) -> dict:
    events = await bg_service.list_task_events(task["task_id"])
    payload = task["payload"]
    result = task["result"] or {}
    error = task["error"] or {}
    report_kind = payload.get("kind") or payload.get("report_kind") or result.get("kind")
    return {
        "task_id": task["task_id"],
        "task_kind": "report",
        "report_kind": report_kind,
        "locale": result.get("locale") or payload.get("locale", "zh"),
        "project_id": task["project_id"],
        "status": _compat_status(task["status"]),
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
        "error": error.get("message"),
        "progress": _progress_from_events(events),
        "summary": result.get("summary") or error.get("message") or "",
    }


async def _serialize_graph_task(task: dict) -> dict:
    events = await bg_service.list_task_events(task["task_id"])
    payload = task["payload"]
    result = task["result"] or {}
    error = task["error"] or {}
    return {
        "task_id": task["task_id"],
        "task_kind": "graph_expansion",
        "project_id": task["project_id"],
        "status": _compat_status(task["status"]),
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
        "error": error.get("message"),
        "progress": _progress_from_events(events),
        "summary": result.get("summary") or error.get("message") or "",
        "runtime_state": result.get("runtime_state"),
        "current_wave": result.get("current_wave"),
        "nodes_discovered": result.get("nodes_discovered"),
        "nodes_explored": result.get("nodes_explored"),
        "graph_project_id": payload.get("project_id") or task["project_id"],
    }


async def _serialize_blog_gen_task(task: dict) -> dict:
    events = await bg_service.list_task_events(task["task_id"])
    payload = task["payload"] or {}
    result = task["result"] or {}
    error = task["error"] or {}
    return {
        "task_id": task["task_id"],
        "task_kind": "blog_generation",
        "project_id": task["project_id"],
        "status": _compat_status(task["status"]),
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
        "error": error.get("message"),
        "progress": _progress_from_events(events),
        "summary": result.get("summary") or error.get("message") or "",
        "style": payload.get("style"),
        "language": result.get("language") or payload.get("language"),
        "skill_id": result.get("skill_id") or payload.get("skill_id"),
        "skill_name": result.get("skill_name"),
        "marketing_skill": result.get("marketing_skill"),
        "bilingual": payload.get("bilingual", False),
        "draft_ids": result.get("draft_ids", []),
        "quality_scores": result.get("quality_scores"),
    }


async def serialize_background_task(task: dict) -> dict:
    kind = task["kind"]
    if kind == "scan":
        return await _serialize_scan_task(task)
    if kind == "report":
        return await _serialize_report_task(task)
    if kind == "graph_expansion":
        return await _serialize_graph_task(task)
    if kind == "blog_generation":
        return await _serialize_blog_gen_task(task)
    # Fallback for unrecognized kinds (e.g. github_enrich)
    events = await bg_service.list_task_events(task["task_id"])
    result = task["result"] or {}
    error = task["error"] or {}
    return {
        "task_id": task["task_id"],
        "task_kind": kind,
        "project_id": task["project_id"],
        "status": _compat_status(task["status"]),
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
        "error": error.get("message"),
        "progress": _progress_from_events(events),
        "summary": result.get("summary") or error.get("message") or "",
    }


@router.get("/tasks")
async def api_v1_tasks(request: Request):
    account_id = await get_request_account_id(request)
    tasks = await bg_service.list_tasks(limit=200)
    visible = [task for task in tasks if await _task_visible(task, account_id)]
    return JSONResponse([await serialize_background_task(task) for task in visible])


@router.get("/tasks/{task_id}")
async def api_v1_task(task_id: str, request: Request):
    record = await bg_service.get_task(task_id)
    if record is None:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not await _task_visible(record, await get_request_account_id(request)):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(await serialize_background_task(record))


@router.get("/tasks/{task_id}/artifacts")
async def api_v1_task_artifacts(task_id: str, request: Request):
    record = await bg_service.get_task(task_id)
    if record is None:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not await _task_visible(record, await get_request_account_id(request)):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if record["kind"] != "scan":
        return JSONResponse({"error": "Artifacts are only available for scan tasks"}, status_code=400)
    return JSONResponse(await _serialize_scan_artifacts(record))


@router.get("/tasks/{task_id}/findings")
async def api_v1_task_findings(task_id: str, request: Request):
    record = await bg_service.get_task(task_id)
    account_id = await get_request_account_id(request)
    if record is not None and not await _task_visible(record, account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if record is None and not await _scan_run_visible(task_id, account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(await storage.get_task_findings(task_id))


@router.get("/tasks/{task_id}/recommendations")
async def api_v1_task_recommendations(task_id: str, request: Request):
    record = await bg_service.get_task(task_id)
    account_id = await get_request_account_id(request)
    if record is not None and not await _task_visible(record, account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if record is None and not await _scan_run_visible(task_id, account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(await storage.get_task_recommendations(task_id))


@router.patch("/tasks/{task_id}/notes")
async def api_v1_task_update_notes(task_id: str, body: dict, request: Request):
    """Update the editable notes/summary for a completed scan run."""
    record = await bg_service.get_task(task_id)
    account_id = await get_request_account_id(request)
    if record is not None and not await _task_visible(record, account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if record is None and not await _scan_run_visible(task_id, account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    notes = body.get("notes", "")
    await storage.update_scan_run_notes(task_id, notes)
    return JSONResponse({"ok": True})


@router.get("/monitors/{monitor_id}/runs")
async def api_v1_monitor_runs(monitor_id: int, request: Request):
    account_id = await get_request_account_id(request)
    if not await storage.get_scheduled_job(monitor_id, account_id=account_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(await storage.list_scan_runs_by_monitor(monitor_id))
