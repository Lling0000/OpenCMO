"""Recursive boundary-aware parent/child chunks with exact source spans."""
from __future__ import annotations

import re
import uuid
from dataclasses import replace

from opencmo.rag.config import RagSettings
from opencmo.rag.text import tokens
from opencmo.rag.types import Chunk, ParsedDocument


def _fit(text: str, start: int, end: int, budget: int) -> int:
    lo, hi = start, end
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if tokens(text[start:mid]) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return lo

def _ranges(text: str, start: int, end: int, budget: int, overlap: int = 0):
    while start < end:
        stop = _fit(text, start, end, budget)
        if stop <= start:
            raise ValueError("token_budget_too_small")
        if stop < end:
            lower = start + (stop - start) // 2
            for pattern in (r"\n\s*\n", r"\n", r"[。！？.!?；;]\s*", r"\s+"):
                matches = list(re.finditer(pattern, text[lower:stop]))
                if matches:
                    stop = lower + matches[-1].end()
                    break
        yield start, stop
        if stop == end:
            break
        next_start = stop
        if overlap:
            lo, hi = start + 1, stop
            while lo < hi:
                mid = (lo + hi) // 2
                if tokens(text[mid:stop]) <= overlap:
                    hi = mid
                else:
                    lo = mid + 1
            next_start = lo
        start = max(start + 1, next_start)

def split_document(parsed: ParsedDocument, generation_id: str, settings: RagSettings) -> list[Chunk]:
    text = parsed.text
    groups = []
    for block in parsed.blocks:
        if groups:
            old = groups[-1]
            if (old.heading, old.page, old.kind) == (block.heading, block.page, block.kind) and tokens(text[old.start:block.end]) <= settings.parent_tokens:
                groups[-1] = replace(old, end=block.end)
                continue
        groups.append(block)
    chunks = []
    for block in groups:
        for start, end in _ranges(text, block.start, block.end, settings.parent_tokens):
            parent_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{generation_id}:parent:{start}:{end}"))
            chunks.append(Chunk(parent_id, None, "parent", start, end, text[start:end], block.heading, block.page, block.prefix))
            for child_start, child_end in _ranges(text, start, end, settings.child_tokens, settings.overlap_tokens):
                if not text[child_start:child_end].strip():
                    continue
                child_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{generation_id}:child:{child_start}:{child_end}"))
                chunks.append(Chunk(child_id, parent_id, "child", child_start, child_end, text[child_start:child_end], block.heading, block.page, block.prefix))
    return chunks

