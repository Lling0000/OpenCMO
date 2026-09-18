"""In-process worker for unified background tasks.

Concurrency is bounded by *max_concurrency* (total in-flight tasks) and
optional per-kind limits via *kind_concurrency*.  Claim uses an atomic
``BEGIN IMMEDIATE`` transaction in storage so multi-process deployments
remain safe.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import Awaitable, Callable

from opencmo.background import service as bg_service
from opencmo.background.types import make_worker_id

Executor = Callable[["ExecutorContext"], Awaitable[None]]
logger = logging.getLogger(__name__)


class ExecutorContext:
    def __init__(self, task: dict, *, worker_id: str):
        self.task = task
        self.worker_id = worker_id

    async def emit(
        self,
        *,
        event_type: str = "progress",
        phase: str = "",
        status: str = "",
        summary: str = "",
        payload: dict | None = None,
    ) -> None:
        await bg_service.append_event(
            self.task["task_id"],
            event_type=event_type,
            phase=phase,
            status=status,
            summary=summary,
            payload=payload or {},
        )

    async def complete(self, result: dict) -> bool:
        return await bg_service.complete_task(self.task["task_id"], result=result, worker_id=self.worker_id)

    async def fail(self, error: dict) -> bool:
        return await bg_service.fail_task(self.task["task_id"], error=error, worker_id=self.worker_id)


class BackgroundWorker:
    """Polls for queued tasks and dispatches them to registered executors.

    Parameters
    ----------
    max_concurrency:
        Global upper bound on in-flight tasks across all kinds.
    kind_concurrency:
        Per-kind upper bound (e.g. ``{"scan": 2, "report": 1}``).
        Kinds not listed fall back to *max_concurrency*.
    """

    def __init__(
        self,
        *,
        poll_interval: float = 0.5,
        stale_after_seconds: int = 300,
        max_concurrency: int = 4,
        kind_concurrency: dict[str, int] | None = None,
        heartbeat_interval: float = 5.0,
    ):
        self.poll_interval = poll_interval
        self.stale_after_seconds = stale_after_seconds
        self.worker_id = make_worker_id()
        self.max_concurrency = max_concurrency
        self.heartbeat_interval = heartbeat_interval
        self._loop_task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._executors: dict[str, Executor] = {}
        self._running_tasks: set[asyncio.Task] = set()
        # Concurrency gates — created lazily on first start()
        self._global_sem: asyncio.Semaphore | None = None
        self._kind_limits = kind_concurrency or {}
        self._kind_sems: dict[str, asyncio.Semaphore] = {}

    def _get_kind_sem(self, kind: str) -> asyncio.Semaphore | None:
        if kind not in self._kind_limits:
            return None
        if kind not in self._kind_sems:
            self._kind_sems[kind] = asyncio.Semaphore(self._kind_limits[kind])
        return self._kind_sems[kind]

    def register_executor(self, kind: str, executor: Executor) -> None:
        self._executors[kind] = executor

    async def start(self) -> None:
        if self._loop_task is not None:
            return
        self._stop.clear()
        self._global_sem = asyncio.Semaphore(self.max_concurrency)
        self._kind_sems.clear()

        # Recover tasks left in running/claimed from a previous worker lifetime
        try:
            recovered = await bg_service.recover_orphaned_tasks(
                stale_after_seconds=self.stale_after_seconds,
            )
            if recovered:
                logger.info(
                    "Startup recovery: requeued/failed %d orphaned task(s)", recovered
                )
        except Exception:
            logger.exception("Startup recovery failed — continuing anyway")

        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._loop_task is None:
            return
        self._stop.set()
        await self._loop_task
        self._loop_task = None
        if self._running_tasks:
            for task in list(self._running_tasks):
                task.cancel()
            await asyncio.gather(*self._running_tasks, return_exceptions=True)

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            await bg_service.recover_stale_tasks(stale_after_seconds=self.stale_after_seconds)

            if self._global_sem is None:
                await asyncio.sleep(self.poll_interval)
                continue

            try:
                await asyncio.wait_for(self._global_sem.acquire(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                continue

            task = await bg_service.claim_next_task(worker_id=self.worker_id)
            if task is None:
                self._global_sem.release()
                await asyncio.sleep(self.poll_interval)
                continue

            execution = asyncio.create_task(self._run_claimed_task(task))
            self._running_tasks.add(execution)
            execution.add_done_callback(self._running_tasks.discard)

    async def _run_claimed_task(self, task: dict) -> None:
        kind = task["kind"]
        kind_sem = self._get_kind_sem(kind)
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(task["task_id"]))
        cancel_watch_task = asyncio.create_task(self._cancel_watch_loop(task["task_id"], asyncio.current_task()))
        acquired_kind_sem = False

        try:
            if kind_sem is not None:
                await kind_sem.acquire()
                acquired_kind_sem = True
            await self._execute_task(task)
        except asyncio.CancelledError:
            current = await bg_service.get_task(task["task_id"])
            if current and current["status"] == "cancel_requested":
                await bg_service.cancel_task(task["task_id"], worker_id=self.worker_id)
            elif current and current["status"] in {"claimed", "running"}:
                await bg_service.requeue_task(
                    task["task_id"],
                    worker_id=self.worker_id,
                    summary="Task requeued after worker cancellation",
                )
            raise
        finally:
            heartbeat_task.cancel()
            cancel_watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            with contextlib.suppress(asyncio.CancelledError):
                await cancel_watch_task
            if acquired_kind_sem and kind_sem is not None:
                kind_sem.release()
            if self._global_sem is not None:
                self._global_sem.release()

    async def _execute_task(self, task: dict) -> None:
        from opencmo import llm, storage

        payload = task.get("payload", {}) or {}

        # Inject BYOK + account context if present in task payload so the worker
        # resolves per-account settings (Reddit/Twitter/SMTP) the same way the
        # original web request would have.
        byok_keys = payload.get("_byok_keys", {})
        byok_token = llm.set_request_keys(byok_keys) if byok_keys else None

        account_id = payload.get("_account_id")
        acct_token = None
        snap_token = None
        if account_id:
            try:
                account_id = int(account_id)
            except (TypeError, ValueError):
                account_id = None
        if account_id:
            acct_token = llm.set_current_account_id(account_id)
            try:
                snapshot = await storage.list_account_settings(account_id)
            except Exception:
                snapshot = {}
            snap_token = llm.set_current_account_settings(snapshot)

        try:
            executor = self._executors[task["kind"]]
            marked = await bg_service.mark_task_running(task["task_id"], worker_id=self.worker_id)
            if not marked:
                current = await bg_service.get_task(task["task_id"])
                if current and current["status"] == "cancel_requested":
                    await bg_service.cancel_task(task["task_id"], worker_id=self.worker_id)
                return
            fresh = await bg_service.get_task(task["task_id"])
            await executor(ExecutorContext(fresh, worker_id=self.worker_id))
            current = await bg_service.get_task(task["task_id"])
            if current and current["status"] == "cancel_requested":
                await bg_service.cancel_task(task["task_id"], worker_id=self.worker_id)
        except Exception as exc:
            await bg_service.retry_or_fail_task(task["task_id"], worker_id=self.worker_id, error={"message": str(exc)})
        finally:
            if snap_token is not None:
                llm.reset_current_account_settings(snap_token)
            if acct_token is not None:
                llm.reset_current_account_id(acct_token)
            if byok_token:
                llm.reset_request_keys(byok_token)

    async def _cancel_watch_loop(self, task_id: str, task: asyncio.Task | None) -> None:
        if task is None:
            return
        while True:
            await asyncio.sleep(min(1.0, self.heartbeat_interval))
            current = await bg_service.get_task(task_id)
            if current is None or current["status"] in {"completed", "failed", "cancelled"}:
                return
            if current["status"] == "cancel_requested":
                task.cancel()
                return

    async def _heartbeat_loop(self, task_id: str) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            ok = await bg_service.heartbeat(task_id, worker_id=self.worker_id)
            if not ok:
                return


_default_worker: BackgroundWorker | None = None


def _get_positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, value)


def _default_kind_concurrency() -> dict[str, int]:
    return {
        "scan": _get_positive_int_env("OPENCMO_SCAN_CONCURRENCY", 1),
        "report": _get_positive_int_env("OPENCMO_REPORT_CONCURRENCY", 1),
        "graph_expansion": _get_positive_int_env("OPENCMO_GRAPH_EXPANSION_CONCURRENCY", 1),
        "github_enrich": _get_positive_int_env("OPENCMO_GITHUB_ENRICH_CONCURRENCY", 1),
        "blog_generation": _get_positive_int_env("OPENCMO_BLOG_GENERATION_CONCURRENCY", 1),
        "knowledge": _get_positive_int_env("OPENCMO_KNOWLEDGE_CONCURRENCY", 1),
    }


def get_background_worker() -> BackgroundWorker:
    global _default_worker
    if _default_worker is None:
        _default_worker = BackgroundWorker(
            max_concurrency=_get_positive_int_env("OPENCMO_WORKER_MAX_CONCURRENCY", 4),
            kind_concurrency=_default_kind_concurrency(),
        )
    return _default_worker
