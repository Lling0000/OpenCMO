from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from opencmo.background import service as bg_service
from opencmo.background import storage as bg_storage
from opencmo.background.executors.report import run_report_executor
from opencmo.background.worker import BackgroundWorker


@pytest.mark.asyncio
async def test_worker_claims_and_completes_executor_task(tmp_path, monkeypatch):
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Worker", "https://worker.test", "saas")

    task = await bg_service.enqueue_task(
        kind="scan",
        project_id=project_id,
        payload={"project_id": project_id},
        dedupe_key=f"scan:monitor:{project_id}",
    )

    completed = asyncio.Event()

    async def _executor(ctx):
        await ctx.complete({"ok": True})
        completed.set()

    worker = BackgroundWorker(poll_interval=0.01, stale_after_seconds=60)
    worker.register_executor("scan", _executor)

    await worker.start()
    try:
        await asyncio.wait_for(completed.wait(), timeout=3.0)
    finally:
        await worker.stop()

    updated = await bg_service.get_task(task["task_id"])
    assert updated["status"] == "completed"
    assert updated["result"]["ok"] is True


@pytest.mark.asyncio
async def test_worker_stop_cancels_inflight_executor(tmp_path, monkeypatch):
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Stopping", "https://stopping.test", "saas")

    await bg_service.enqueue_task(
        kind="scan",
        project_id=project_id,
        payload={
            "monitor_id": 77,
            "project_id": project_id,
            "job_type": "full",
            "job_id": 77,
        },
        dedupe_key="scan:monitor:77",
    )

    started = asyncio.Event()

    async def _executor(_ctx):
        started.set()
        await asyncio.Future()

    worker = BackgroundWorker(poll_interval=0.01, stale_after_seconds=60)
    worker.register_executor("scan", _executor)

    await worker.start()
    await asyncio.wait_for(started.wait(), timeout=1.0)
    await asyncio.wait_for(worker.stop(), timeout=1.0)


@pytest.mark.asyncio
async def test_worker_respects_max_concurrency(tmp_path, monkeypatch):
    """Worker should not run more tasks concurrently than max_concurrency."""
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Conc", "https://conc.test", "saas")

    # Enqueue 4 tasks but allow only 2 concurrent
    for i in range(4):
        await bg_service.enqueue_task(
            kind="scan",
            project_id=project_id,
            payload={"i": i},
            dedupe_key=None,
        )

    peak_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()
    gate = asyncio.Event()

    async def _slow_executor(ctx):
        nonlocal peak_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            peak_concurrent = max(peak_concurrent, current_concurrent)
        # Wait until gate opens — simulates long task
        await asyncio.wait_for(gate.wait(), timeout=2.0)
        async with lock:
            current_concurrent -= 1
        await ctx.complete({"ok": True})

    worker = BackgroundWorker(
        poll_interval=0.01,
        stale_after_seconds=60,
        max_concurrency=2,
    )
    worker.register_executor("scan", _slow_executor)

    await worker.start()
    # Let worker claim and start executing
    await asyncio.sleep(0.15)
    # Release all tasks
    gate.set()
    await asyncio.sleep(0.3)
    await worker.stop()

    assert peak_concurrent <= 2


@pytest.mark.asyncio
async def test_worker_respects_kind_concurrency(tmp_path, monkeypatch):
    """Per-kind semaphore should limit concurrency within a single kind."""
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Kind", "https://kind.test", "saas")

    for i in range(3):
        await bg_service.enqueue_task(
            kind="report",
            project_id=project_id,
            payload={"i": i},
            dedupe_key=None,
        )

    peak_report = 0
    current_report = 0
    lock = asyncio.Lock()
    gate = asyncio.Event()

    async def _report_executor(ctx):
        nonlocal peak_report, current_report
        async with lock:
            current_report += 1
            peak_report = max(peak_report, current_report)
        await asyncio.wait_for(gate.wait(), timeout=2.0)
        async with lock:
            current_report -= 1
        await ctx.complete({"ok": True})

    worker = BackgroundWorker(
        poll_interval=0.01,
        stale_after_seconds=60,
        max_concurrency=4,
        kind_concurrency={"report": 1},
    )
    worker.register_executor("report", _report_executor)

    await worker.start()
    await asyncio.sleep(0.15)
    gate.set()
    await asyncio.sleep(0.3)
    await worker.stop()

    assert peak_report <= 1


@pytest.mark.asyncio
async def test_claimed_task_waiting_for_kind_slot_keeps_heartbeat(tmp_path, monkeypatch):
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Heartbeat", "https://heartbeat.test", "saas")

    first = await bg_service.enqueue_task(
        kind="report",
        project_id=project_id,
        payload={"i": 1},
        dedupe_key=None,
    )
    second = await bg_service.enqueue_task(
        kind="report",
        project_id=project_id,
        payload={"i": 2},
        dedupe_key=None,
    )

    first_started = asyncio.Event()
    release_first = asyncio.Event()
    running_task_id: str | None = None

    async def _report_executor(ctx):
        nonlocal running_task_id
        if running_task_id is None:
            running_task_id = ctx.task["task_id"]
            first_started.set()
            await asyncio.wait_for(release_first.wait(), timeout=3.0)
        await ctx.complete({"ok": True})

    worker = BackgroundWorker(
        poll_interval=0.01,
        stale_after_seconds=1,
        max_concurrency=2,
        kind_concurrency={"report": 1},
        heartbeat_interval=0.05,
    )
    worker.register_executor("report", _report_executor)

    await worker.start()
    await asyncio.wait_for(first_started.wait(), timeout=1.0)
    waiting_task_id = second["task_id"] if running_task_id == first["task_id"] else first["task_id"]
    await asyncio.sleep(1.3)

    waiting = await bg_service.get_task(waiting_task_id)
    assert waiting["status"] == "claimed"
    assert waiting["attempt_count"] == 0
    assert waiting["heartbeat_at"] is not None

    release_first.set()
    await asyncio.sleep(0.2)
    await worker.stop()


@pytest.mark.asyncio
async def test_worker_retries_transient_executor_exception(tmp_path, monkeypatch):
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Retry", "https://retry.test", "saas")

    task = await bg_service.enqueue_task(
        kind="scan",
        project_id=project_id,
        payload={"project_id": project_id},
        dedupe_key=None,
        max_attempts=2,
    )

    calls = 0

    async def _flaky_executor(ctx):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary")
        await ctx.complete({"ok": True})

    worker = BackgroundWorker(poll_interval=0.01, stale_after_seconds=60, heartbeat_interval=0.05)
    worker.register_executor("scan", _flaky_executor)

    await worker.start()
    for _ in range(100):
        updated = await bg_service.get_task(task["task_id"])
        if updated["status"] == "completed":
            break
        await asyncio.sleep(0.02)
    await worker.stop()

    updated = await bg_service.get_task(task["task_id"])
    assert calls == 2
    assert updated["status"] == "completed"
    assert updated["attempt_count"] == 1
    assert updated["result"]["ok"] is True


@pytest.mark.asyncio
async def test_worker_fails_transient_exception_after_max_attempts(tmp_path, monkeypatch):
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("RetryFail", "https://retryfail.test", "saas")

    task = await bg_service.enqueue_task(
        kind="scan",
        project_id=project_id,
        payload={"project_id": project_id},
        dedupe_key=None,
        max_attempts=2,
    )

    calls = 0

    async def _always_fails(_ctx):
        nonlocal calls
        calls += 1
        raise RuntimeError("still temporary")

    worker = BackgroundWorker(poll_interval=0.01, stale_after_seconds=60, heartbeat_interval=0.05)
    worker.register_executor("scan", _always_fails)

    await worker.start()
    for _ in range(100):
        updated = await bg_service.get_task(task["task_id"])
        if updated["status"] == "failed":
            break
        await asyncio.sleep(0.02)
    await worker.stop()

    updated = await bg_service.get_task(task["task_id"])
    assert calls == 2
    assert updated["status"] == "failed"
    assert updated["attempt_count"] == 1
    assert updated["error"]["message"] == "still temporary"


@pytest.mark.asyncio
async def test_report_executor_accepts_legacy_report_kind_payload(monkeypatch):
    from opencmo import service

    async def _regenerate(project_id, kind, **_kwargs):
        return {
            "human": {
                "id": 11,
                "version": 1,
                "generation_status": "completed",
                "content": "# Done",
            },
            "agent": {"id": 12, "version": 1},
            "project_id": project_id,
            "kind": kind,
        }

    monkeypatch.setattr(service, "regenerate_project_report", _regenerate)
    completed: dict = {}

    class _Ctx:
        task = {
            "task_id": "report-task",
            "payload": {"project_id": 7, "report_kind": "strategic", "locale": "en"},
        }

        async def emit(self, **_kwargs):
            return None

        async def complete(self, result):
            completed.update(result)
            return True

        async def fail(self, error):
            raise AssertionError(error)

    await run_report_executor(_Ctx())

    assert completed["kind"] == "strategic"
    assert completed["human_report_id"] == 11


@pytest.mark.asyncio
async def test_worker_cancels_running_task_when_cancel_requested(tmp_path, monkeypatch):
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Cancel", "https://cancel.test", "saas")

    task = await bg_service.enqueue_task(
        kind="scan",
        project_id=project_id,
        payload={"project_id": project_id},
        dedupe_key=None,
    )

    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def _executor(_ctx):
        started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    worker = BackgroundWorker(poll_interval=0.01, stale_after_seconds=60, heartbeat_interval=0.02)
    worker.register_executor("scan", _executor)

    await worker.start()
    await asyncio.wait_for(started.wait(), timeout=1.0)
    assert await bg_service.request_cancel(task["task_id"]) is True
    await asyncio.wait_for(cancelled.wait(), timeout=1.0)

    for _ in range(100):
        updated = await bg_service.get_task(task["task_id"])
        if updated["status"] == "cancelled":
            break
        await asyncio.sleep(0.02)
    await worker.stop()

    updated = await bg_service.get_task(task["task_id"])
    assert updated["status"] == "cancelled"


def test_get_background_worker_uses_env_backed_limits(monkeypatch):
    from opencmo.background import worker as worker_module

    monkeypatch.setenv("OPENCMO_WORKER_MAX_CONCURRENCY", "3")
    monkeypatch.setenv("OPENCMO_SCAN_CONCURRENCY", "1")
    monkeypatch.setenv("OPENCMO_REPORT_CONCURRENCY", "2")
    monkeypatch.setenv("OPENCMO_GRAPH_EXPANSION_CONCURRENCY", "4")
    monkeypatch.setenv("OPENCMO_GITHUB_ENRICH_CONCURRENCY", "5")

    original_worker = worker_module._default_worker
    worker_module._default_worker = None
    try:
        worker = worker_module.get_background_worker()
        assert worker.max_concurrency == 3
        assert worker._kind_limits == {
            "scan": 1,
            "report": 2,
            "graph_expansion": 4,
            "github_enrich": 5,
            "blog_generation": 1,
            "knowledge": 1,
        }
    finally:
        worker_module._default_worker = original_worker


@pytest.mark.asyncio
async def test_run_after_delays_task_execution(tmp_path, monkeypatch):
    """Tasks with run_after in the future should not be claimed."""
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Delay", "https://delay.test", "saas")

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    task = await bg_service.enqueue_task(
        kind="scan",
        project_id=project_id,
        payload={"future": True},
        dedupe_key=None,
        run_after=future,
    )

    # Verify the task was saved with run_after
    fetched = await bg_service.get_task(task["task_id"])
    assert fetched["run_after"] == future

    # Worker should NOT claim it (run_after is in the future)
    claimed = await bg_storage.claim_next_queued_task(worker_id="test-worker")
    assert claimed is None


@pytest.mark.asyncio
async def test_dedupe_index_prevents_duplicate_active_tasks(tmp_path, monkeypatch):
    """Partial unique index on dedupe_key should prevent duplicates at DB level."""
    from opencmo import storage

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path, raising=False)
    await storage.ensure_db()
    project_id = await storage.ensure_project("Dupe", "https://dupe.test", "saas")

    await bg_storage.insert_task(
        task_id="dup-1",
        kind="scan",
        project_id=project_id,
        payload={},
        dedupe_key="scan:test:1",
        priority=50,
        max_attempts=3,
    )

    # Second insert with same dedupe_key while first is active should fail
    import aiosqlite
    with pytest.raises(aiosqlite.IntegrityError):
        await bg_storage.insert_task(
            task_id="dup-2",
            kind="scan",
            project_id=project_id,
            payload={},
            dedupe_key="scan:test:1",
            priority=50,
            max_attempts=3,
        )
