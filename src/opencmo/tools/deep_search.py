"""Debuggable deep-search tool with traced planning loops."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

from agents import function_tool

from opencmo.tools.deep_search_trace import record_trace, summarize_text


@dataclass
class DeepSearchStep:
    depth: int
    query: str
    thought: str
    search_summary: str = ""
    read_url: str | None = None
    read_source: str | None = None
    read_summary: str = ""
    error: str | None = None
    children: list["DeepSearchStep"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "query": self.query,
            "thought": self.thought,
            "search_summary": self.search_summary,
            "read_url": self.read_url,
            "read_source": self.read_source,
            "read_summary": self.read_summary,
            "error": self.error,
            "children": [child.to_dict() for child in self.children],
        }


def _breakpoints_enabled() -> bool:
    return os.getenv("OPENCMO_DEEP_SEARCH_BREAKPOINTS", "").strip().lower() in {"1", "true", "on", "yes"}


def _maybe_cli_breakpoint(step: DeepSearchStep) -> str | None:
    """Return an override query, stop marker, or None.

    The breakpoint is intentionally opt-in and TTY-only so web/API deployments never
    block waiting for terminal input.
    """
    if not _breakpoints_enabled() or not sys.stdin.isatty():
        return None

    prompt = (
        f"\n[OpenCMO deep_search breakpoint depth={step.depth}]\n"
        f"Thought: {step.thought}\n"
        f"Next query: {step.query}\n"
        "Press Enter to continue, type 'stop' to end, or type a replacement query: "
    )
    response = input(prompt).strip()
    if not response:
        return None
    if response.lower() in {"stop", "quit", "exit"}:
        return "__STOP__"
    return response


def _extract_first_url(search_text: str) -> str | None:
    for line in search_text.splitlines():
        candidate = line.strip()
        if candidate.startswith(("http://", "https://")):
            return candidate
    return None


def _next_query(original_query: str, step: DeepSearchStep) -> str:
    if step.read_url:
        return f"{original_query} alternatives pricing competitors"
    return f"{original_query} official site case studies"


def _format_tree(steps: list[DeepSearchStep]) -> str:
    parts: list[str] = []
    for step in steps:
        parts.append(
            "\n".join(
                [
                    f"## Step {step.depth}: {step.query}",
                    f"Thought: {step.thought}",
                    f"Search summary: {step.search_summary or 'No search summary.'}",
                    f"Read URL: {step.read_url or 'None'}",
                    f"Read source: {step.read_source or 'None'}",
                    f"Read summary: {step.read_summary or 'No page read.'}",
                    f"Error: {step.error or 'None'}",
                ]
            )
        )
    return "\n\n".join(parts)


async def run_deep_search(query: str, *, max_depth: int = 2, read_chars: int = 4000) -> dict[str, Any]:
    """Run a traced Search -> Read -> Search loop and return structured state."""
    max_depth = max(1, min(max_depth, 5))
    read_chars = max(500, min(read_chars, 20000))

    steps: list[DeepSearchStep] = []
    current_query = query

    for depth in range(1, max_depth + 1):
        step = DeepSearchStep(
            depth=depth,
            query=current_query,
            thought=(
                "Start broad, inspect the strongest source, then refine the query "
                "based on what the page reveals."
            ),
        )

        override = _maybe_cli_breakpoint(step)
        if override == "__STOP__":
            step.error = "Stopped by CLI breakpoint."
            steps.append(step)
            break
        if override:
            step.query = override
            current_query = override

        try:
            from opencmo.tools.tavily_helper import tavily_search

            results = await tavily_search(current_query, max_results=3, search_depth="basic")
            if results:
                search_lines = []
                for result in results:
                    search_lines.append(f"{result.title}\n{result.url}\n{result.snippet}")
                search_text = "\n\n".join(search_lines)
            else:
                search_text = ""
            step.search_summary = summarize_text(search_text)
            step.read_url = _extract_first_url(search_text)
            record_trace(
                tool="deep_search",
                action="search",
                payload={"query": current_query, "depth": depth, "max_results": 3},
                provider="tavily",
                output=search_text,
                metadata={"tree": [item.to_dict() for item in steps + [step]]},
            )
        except Exception as exc:
            step.error = f"Search failed: {exc}"
            record_trace(
                tool="deep_search",
                action="search",
                payload={"query": current_query, "depth": depth, "max_results": 3},
                provider="tavily",
                error=str(exc),
                metadata={"tree": [item.to_dict() for item in steps + [step]]},
            )
            steps.append(step)
            break

        if step.read_url:
            try:
                from opencmo.tools.crawl import fetch_url_content

                content, source = await fetch_url_content(step.read_url, max_chars=read_chars)
                step.read_source = source
                step.read_summary = summarize_text(content, max_chars=900)
                record_trace(
                    tool="deep_search",
                    action="read",
                    payload={"url": step.read_url, "depth": depth, "read_chars": read_chars},
                    provider=source,
                    output=content,
                    metadata={"tree": [item.to_dict() for item in steps + [step]]},
                )
            except Exception as exc:
                step.error = f"Read failed: {exc}"
                record_trace(
                    tool="deep_search",
                    action="read",
                    payload={"url": step.read_url, "depth": depth, "read_chars": read_chars},
                    error=str(exc),
                    metadata={"tree": [item.to_dict() for item in steps + [step]]},
                )

        steps.append(step)
        if depth < max_depth:
            current_query = _next_query(query, step)

    return {
        "query": query,
        "max_depth": max_depth,
        "steps": [step.to_dict() for step in steps],
        "summary": _format_tree(steps),
    }


@function_tool
async def deep_search(query: str, max_depth: int = 2) -> str:
    """Run a debuggable Search -> Read -> Search research loop.

    Args:
        query: The market, competitor, product, or topic to research.
        max_depth: Number of search/read iterations. Clamped to 1-5.
    """
    result = await run_deep_search(query, max_depth=max_depth)
    return result["summary"]
