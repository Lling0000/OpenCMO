"""Run production chat regressions for single-platform marketing assistants.

Example:
    python -m opencmo.ops.chat_platform_regression \
      --base-url https://www.aidcmo.com/api/v1 \
      --project-id 36
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class PlatformCase:
    platform: str
    prompt: str
    expected_agent: str


DEFAULT_CASES: tuple[PlatformCase, ...] = (
    PlatformCase("Twitter", "帮我写 3 条 Twitter/X 推文和 1 条 thread，推广 OpenCMO。", "Twitter Expert"),
    PlatformCase("LinkedIn", "请给我一组 LinkedIn 营销内容，走 LinkedIn 专家。", "LinkedIn Expert"),
    PlatformCase("Reddit", "Draft a Reddit post for OpenCMO and ask for feedback.", "Reddit Expert"),
    PlatformCase("ProductHunt", "帮我写一套适合 Product Hunt 的发布文案，推广 OpenCMO。", "Product Hunt Expert"),
    PlatformCase("Zhihu", "帮我写一篇知乎回答，主题是 AI 搜索品牌监控。", "Zhihu Expert"),
    PlatformCase("Xiaohongshu", "帮我写一篇小红书笔记，推广 OpenCMO。", "Xiaohongshu Expert"),
    PlatformCase("WeChat", "帮我写一篇适合发在微信公众号的文章，推广 OpenCMO。", "WeChat Expert"),
    PlatformCase("Jike", "帮我写一条即刻动态，主题是 AI 搜索里的品牌监控正在变重要。", "Jike Expert"),
    PlatformCase("Juejin", "帮我写一篇适合发在掘金的技术文章，推广 OpenCMO。", "Juejin Expert"),
    PlatformCase("V2EX", "帮我写一篇 V2EX 帖子，介绍 OpenCMO 做 AI 搜索品牌监控。", "V2EX Expert"),
    PlatformCase("HackerNews", "Write a Hacker News launch post for OpenCMO.", "Hacker News Expert"),
    PlatformCase("OSChina", "帮我写一篇适合发在 OSChina 的开源项目推荐稿，推广 OpenCMO。", "OSChina Expert"),
    PlatformCase("GitCode", "帮我写一套适合发在 GitCode 的仓库介绍和配套文章，推广 OpenCMO。", "GitCode Expert"),
    PlatformCase("Sspai", "帮我写一篇适合发在少数派的文章，推广 OpenCMO。", "Sspai Expert"),
    PlatformCase("InfoQ", "帮我写一篇适合发在 InfoQ 的技术文章，推广 OpenCMO。", "InfoQ Expert"),
    PlatformCase("Devto", "帮我写一篇适合发在 Dev.to 的英文风格技术文章，推广 OpenCMO。", "Devto Expert"),
    PlatformCase("Ruanyifeng", "帮我写一条阮一峰周刊投稿，主题是 OpenCMO。", "Ruanyifeng Weekly Expert"),
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://www.aidcmo.com/api/v1")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--locale", default="zh")
    parser.add_argument("--connect-timeout", type=float, default=30.0)
    parser.add_argument("--read-timeout", type=float, default=60.0)
    parser.add_argument("--platform", action="append", help="Run only the named platform(s)")
    parser.add_argument("--json", action="store_true", help="Emit JSON lines only")
    parser.add_argument("--auth-token-env", default="OPENCMO_WEB_TOKEN", help="Environment variable containing the bearer token")
    parser.add_argument("--require-auth", action="store_true", help="Fail before requests when the bearer token is missing")
    parser.add_argument("--fail-on-incomplete", action="store_true", help="Exit non-zero when any case is incomplete")
    return parser.parse_args(argv)


def select_cases(platform_filters: list[str] | None) -> list[PlatformCase]:
    if not platform_filters:
        return list(DEFAULT_CASES)
    requested = {value.strip().lower() for value in platform_filters if value.strip()}
    return [case for case in DEFAULT_CASES if case.platform.lower() in requested]


def make_session(session: requests.Session | None = None, *, token: str = "") -> requests.Session:
    sess = session or requests.Session()
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[502, 503, 504], allowed_methods=None)
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    if token:
        sess.headers["Authorization"] = f"Bearer {token}"
    return sess


def _iter_sse_payloads(response: requests.Response) -> Iterable[dict]:
    for raw in response.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        payload = raw[6:]
        if payload == "[DONE]":
            break
        yield json.loads(payload)


def run_case(
    session: requests.Session,
    *,
    base_url: str,
    project_id: int,
    locale: str,
    case: PlatformCase,
    connect_timeout: float,
    read_timeout: float,
) -> dict:
    result = {
        "platform": case.platform,
        "expected_agent": case.expected_agent,
        "agent": None,
        "done": False,
        "stream_timed_out": None,
        "error": None,
        "final_preview": "",
    }
    chunks: list[str] = []
    try:
        session_resp = session.post(
            f"{base_url}/chat/sessions",
            json={"project_id": project_id},
            timeout=connect_timeout,
        )
        session_resp.raise_for_status()
        session_id = session_resp.json()["session_id"]
    except Exception as exc:  # noqa: BLE001 - operational script
        result["error"] = f"session_create_failed: {exc}"
        return result

    try:
        response = session.post(
            f"{base_url}/chat",
            headers={"Accept": "text/event-stream"},
            json={
                "message": case.prompt,
                "session_id": session_id,
                "project_id": project_id,
                "locale": locale,
            },
            stream=True,
            timeout=(connect_timeout, read_timeout),
        )
    except Exception as exc:  # noqa: BLE001 - operational script
        result["error"] = f"chat_request_failed: {exc}"
        return result

    try:
        response.raise_for_status()
        for event in _iter_sse_payloads(response):
            event_type = event.get("type")
            if event_type == "agent":
                result["agent"] = event.get("name")
            elif event_type == "delta":
                chunk = event.get("content") or event.get("delta") or ""
                if chunk:
                    chunks.append(chunk)
            elif event_type == "done":
                result["done"] = True
                result["stream_timed_out"] = event.get("stream_timed_out")
                final_output = event.get("final_output") or "".join(chunks)
                result["final_preview"] = final_output[:300]
                break
            elif event_type == "error":
                result["error"] = event.get("message") or event.get("detail") or str(event)
                result["final_preview"] = "".join(chunks)[:300]
                break
    except Exception as exc:  # noqa: BLE001 - operational script
        result["error"] = str(exc)
        result["final_preview"] = "".join(chunks)[:300]
    finally:
        response.close()
    return result


def _emit(result: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
        return
    summary = (
        f"[{result['platform']}] agent={result['agent']} expected={result['expected_agent']} "
        f"done={result['done']} stream_timed_out={result['stream_timed_out']}"
    )
    if result["error"]:
        summary += f" error={result['error']}"
    print(summary)
    if result["final_preview"]:
        print(result["final_preview"])
        print()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cases = select_cases(args.platform)
    if not cases:
        print("No matching platforms selected.", file=sys.stderr)
        return 2

    token = os.environ.get(args.auth_token_env, "").strip()
    if args.require_auth and not token:
        for case in cases:
            _emit({
                "platform": case.platform, "expected_agent": case.expected_agent,
                "agent": None, "done": False, "stream_timed_out": None,
                "error": "authentication_not_configured: required bearer token environment variable is empty",
                "final_preview": "",
            }, as_json=args.json)
        return 2
    session = make_session(token=token)
    results = []
    for case in cases:
        result = run_case(
            session,
            base_url=args.base_url.rstrip("/"),
            project_id=args.project_id,
            locale=args.locale,
            case=case,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
        )
        results.append(result)
        _emit(result, as_json=args.json)

    if args.fail_on_incomplete:
        failed = [
            item
            for item in results
            if item["agent"] != item["expected_agent"] or not item["done"] or item["error"] or item["stream_timed_out"]
        ]
        if failed:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
