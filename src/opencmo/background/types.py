"""Types and constants for the unified background task runtime."""

from __future__ import annotations

import os
import socket
import uuid
from dataclasses import dataclass

TASK_KINDS = frozenset({"scan", "report", "graph_expansion", "github_enrich", "blog_generation", "knowledge"})
ACTIVE_STATUSES = frozenset({"queued", "claimed", "running", "cancel_requested"})
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def make_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class TaskEventInput:
    event_type: str
    phase: str = ""
    status: str = ""
    summary: str = ""
    payload: dict | None = None

