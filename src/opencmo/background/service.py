"""High-level lifecycle service for unified background tasks."""

from __future__ import annotations

import uuid

from opencmo.background import storage as bg_storage


async def enqueue_task(
    *,
    kind: str,
    project_id: int | None,
    payload: dict,
    dedupe_key: str | None,
    priority: int = 50,
    max_attempts: int = 3,
    run_after: str | None = None,
) -> dict:
    from opencmo import llm

    # Capture BYOK keys + active account id from current request context so
    # the worker can restore them when the task actually runs.
    keys = {} if kind == "knowledge" else llm.get_request_keys()
    account_id = llm.get_current_account_id()
    if keys or account_id:
        payload = payload.copy()
        if keys:
            payload["_byok_keys"] = keys
        if account_id:
            payload["_account_id"] = int(account_id)

    if dedupe_key:

        existing = await bg_storage.find_active_task_by_dedupe_key(dedupe_key)
        if existing is not None:
            return existing

    task_id = str(uuid.uuid4())
    await bg_storage.insert_task(
        task_id=task_id,
        kind=kind,
        project_id=project_id,
        payload=payload,
        dedupe_key=dedupe_key,
        priority=priority,
        max_attempts=max_attempts,
        run_after=run_after,
    )
    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status="queued",
        summary=f"{kind} task queued",
        payload={"kind": kind},
    )
    return await bg_storage.get_task(task_id)


async def get_task(task_id: str) -> dict | None:
    return await bg_storage.get_task(task_id)


async def list_tasks(*, kind: str | None = None, limit: int = 100) -> list[dict]:
    return await bg_storage.list_tasks(kind=kind, limit=limit)


async def list_task_events(task_id: str) -> list[dict]:
    return await bg_storage.list_task_events(task_id)


async def find_active_task_by_dedupe_key(dedupe_key: str) -> dict | None:
    return await bg_storage.find_active_task_by_dedupe_key(dedupe_key)


async def claim_next_task(*, worker_id: str) -> dict | None:
    return await bg_storage.claim_next_queued_task(worker_id=worker_id)


async def mark_task_running(task_id: str, *, worker_id: str) -> bool:
    updated = await bg_storage.mark_task_running(task_id, worker_id=worker_id)
    if not updated:
        return False
    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status="running",
        summary="Task started",
    )
    return True


async def heartbeat(task_id: str, *, worker_id: str) -> bool:
    return await bg_storage.heartbeat(task_id, worker_id=worker_id)


async def append_event(
    task_id: str,
    *,
    event_type: str,
    phase: str = "",
    status: str = "",
    summary: str = "",
    payload: dict | None = None,
) -> int:
    return await bg_storage.append_task_event(
        task_id,
        event_type=event_type,
        phase=phase,
        status=status,
        summary=summary,
        payload=payload,
    )


async def request_cancel(task_id: str) -> bool:
    status = await bg_storage.request_cancel_task(task_id)
    if status is None:
        return False

    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status=status,
        summary="Task cancelled" if status == "cancelled" else "Cancellation requested",
    )
    return True


async def complete_task(task_id: str, *, result: dict | None = None, worker_id: str | None = None) -> bool:
    updated = await bg_storage.complete_task(task_id, result=result or {}, worker_id=worker_id)
    if not updated:
        return False
    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status="completed",
        summary="Task completed",
        payload=result or {},
    )
    return True


async def fail_task(task_id: str, *, error: dict, worker_id: str | None = None) -> bool:
    task = await bg_storage.get_task(task_id)
    updated = await bg_storage.fail_task(task_id, error=error, worker_id=worker_id)
    if not updated:
        return False
    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status="failed",
        summary=error.get("message", "Task failed"),
        payload=error,
    )
    # Keep scan_runs table in sync when a scan task is failed externally
    if task and task.get("kind") == "scan":
        try:
            from opencmo.storage import fail_scan_run_by_task_id
            await fail_scan_run_by_task_id(task_id, error.get("message", "Task failed"))
        except Exception:
            pass
    return True


async def cancel_task(task_id: str, *, worker_id: str | None = None) -> bool:
    updated = await bg_storage.cancel_task(task_id, worker_id=worker_id)
    if not updated:
        return False
    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status="cancelled",
        summary="Task cancelled",
    )
    return True


async def requeue_task(
    task_id: str,
    *,
    worker_id: str | None = None,
    summary: str = "Task requeued",
) -> bool:
    updated = await bg_storage.requeue_task(task_id, worker_id=worker_id)
    if not updated:
        return False
    await bg_storage.append_task_event(
        task_id,
        event_type="state_change",
        status="queued",
        summary=summary,
    )
    return True


async def retry_or_fail_task(task_id: str, *, worker_id: str, error: dict) -> bool:
    task = await bg_storage.get_task(task_id)
    if task is None:
        return False

    if task["status"] == "cancel_requested":
        return await cancel_task(task_id, worker_id=worker_id)

    next_attempt = int(task["attempt_count"]) + 1
    if next_attempt < int(task["max_attempts"]):
        return await requeue_task(
            task_id,
            worker_id=worker_id,
            summary=f"Task failed transiently; retrying attempt {next_attempt + 1}",
        )

    return await fail_task(task_id, error=error, worker_id=worker_id)


async def recover_orphaned_tasks(*, stale_after_seconds: int) -> int:
    """Recover tasks left in running/claimed from a previous worker lifetime.

    Unlike ``recover_stale_tasks`` (which only looks at non-NULL heartbeats),
    this also catches tasks whose heartbeat is NULL — e.g. tasks that were
    claimed but never started before the process died.
    """
    stale_before = bg_storage.stale_cutoff(stale_after_seconds=stale_after_seconds)
    orphaned = await bg_storage.list_orphaned_tasks(stale_after_seconds=stale_after_seconds)
    fixed = 0
    for task in orphaned:
        next_attempt = int(task["attempt_count"]) + 1
        if next_attempt < int(task["max_attempts"]):
            updated = await bg_storage.requeue_stale_task(
                task["task_id"],
                worker_id=task["worker_id"],
                stale_before=stale_before,
            )
            if not updated:
                continue
            await bg_storage.append_task_event(
                task["task_id"],
                event_type="state_change",
                status="queued",
                summary="Task requeued after worker restart recovery",
            )
        else:
            updated = await bg_storage.fail_stale_task(
                task["task_id"],
                worker_id=task["worker_id"],
                stale_before=stale_before,
                error={"message": "Task exceeded max attempts (recovered after restart)"},
            )
            if not updated:
                continue
            await bg_storage.append_task_event(
                task["task_id"],
                event_type="state_change",
                status="failed",
                summary="Task exceeded max attempts (recovered after restart)",
                payload={"message": "Task exceeded max attempts (recovered after restart)"},
            )
        fixed += 1
    return fixed


async def recover_stale_tasks(*, stale_after_seconds: int) -> int:
    stale_before = bg_storage.stale_cutoff(stale_after_seconds=stale_after_seconds)
    stale_tasks = await bg_storage.list_stale_tasks(stale_after_seconds=stale_after_seconds)
    fixed = 0
    for task in stale_tasks:
        next_attempt = int(task["attempt_count"]) + 1
        if next_attempt < int(task["max_attempts"]):
            updated = await bg_storage.requeue_stale_task(
                task["task_id"],
                worker_id=task["worker_id"],
                stale_before=stale_before,
            )
            if not updated:
                continue
            await bg_storage.append_task_event(
                task["task_id"],
                event_type="state_change",
                status="queued",
                summary="Task requeued after stale heartbeat",
            )
        else:
            updated = await bg_storage.fail_stale_task(
                task["task_id"],
                worker_id=task["worker_id"],
                stale_before=stale_before,
                error={"message": "Task exceeded max attempts after stale heartbeat"},
            )
            if not updated:
                continue
            await bg_storage.append_task_event(
                task["task_id"],
                event_type="state_change",
                status="failed",
                summary="Task exceeded max attempts after stale heartbeat",
                payload={"message": "Task exceeded max attempts after stale heartbeat"},
            )
        fixed += 1
    return fixed
