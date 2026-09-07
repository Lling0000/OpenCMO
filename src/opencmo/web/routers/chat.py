"""Chat API router (SSE streaming)."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from opencmo import storage
from opencmo.opportunities import build_project_opportunity_snapshot
from opencmo.web.auth import get_request_account_id, get_request_user_id

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

_STREAM_FIRST_EVENT_TIMEOUT_SECONDS = 120.0
_STREAM_IDLE_EVENT_TIMEOUT_SECONDS = 20.0
_MARKETING_REVIEW_TIMEOUT_SECONDS = 30.0


@router.get("/chat/context/{project_id}")
async def api_v1_chat_context(project_id: int, request: Request):
    """Return structured project context for the Chat UI."""
    account_id = await get_request_account_id(request)
    project = await storage.get_project(project_id, account_id=account_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    # Latest scan scores
    latest = await storage.get_latest_scans(project_id)

    # Graph data for competitors, keywords, gaps
    graph = await storage.get_graph_data(project_id)
    nodes = graph.get("nodes", [])
    snapshot = await build_project_opportunity_snapshot(project_id)


    competitors = [
        {"label": n["label"], "url": n.get("url", "")}
        for n in nodes if n.get("type") == "competitor"
    ][:6]

    keywords = [
        n["label"]
        for n in nodes if n.get("type") == "keyword"
    ][:10]

    brand_kw_set = {n["label"].lower() for n in nodes if n.get("type") == "keyword"}
    keyword_gaps = [
        n["label"]
        for n in nodes
        if n.get("type") == "competitor_keyword" and n["label"].lower() not in brand_kw_set
    ][:5]

    # Latest findings from most recent scan run
    from opencmo.storage._db import get_db
    findings = []
    try:
        db = await get_db()
        cursor = await db.execute(
            """SELECT f.domain, f.severity, f.title
               FROM scan_findings f
               JOIN scan_runs r ON r.id = f.run_id
               WHERE r.project_id = ?
               ORDER BY r.id DESC, f.id
               LIMIT 4""",
            (project_id,),
        )
        rows = await cursor.fetchall()
        findings = [
            {"domain": row[0], "severity": row[1], "title": row[2]}
            for row in rows
        ]
        await db.close()
    except Exception:
        pass


    # Scores
    seo = latest.get("seo")
    geo = latest.get("geo")
    community = latest.get("community")
    serp = latest.get("serp", [])

    ctx = {
        "project": {
            "id": project["id"],
            "brand_name": project["brand_name"],
            "url": project["url"],
            "category": project["category"],
        },
        "scores": {
            "seo": seo.get("score") if seo else None,
            "geo": geo.get("score") if geo else None,
            "community_hits": community.get("total_hits") if community else None,
            "serp_tracked": len(serp),
            "serp_top10": sum(1 for s in serp if (s.get("position") or 999) <= 10),
        },
        "keywords": keywords,
        "competitors": competitors,
        "keyword_gaps": keyword_gaps,
        "findings": findings,
        "top_opportunities": [
            {
                "type": item["type"],
                "domain": item["domain"],
                "title": item["title"],
                "priority": item["priority"],
                "score": item["score"],
            }
            for item in snapshot["opportunities"]["top"][:3]
        ],
        "topic_clusters": [
            {
                "name": item["name"],
                "opportunity_score": item["opportunity_score"],
                "gap_keywords": item["gap_keywords"][:3],
            }
            for item in snapshot["cluster_summary"]["top_clusters"][:3]
        ],
        "cluster_gaps": snapshot["cluster_summary"]["gap_keywords"][:5],
    }
    return JSONResponse(ctx)


def _get_item_name(item) -> str:
    """Safely extract tool/handoff name from a RunItem."""
    raw = getattr(item, "raw_item", None)
    if raw is not None and hasattr(raw, "name"):
        return raw.name
    return getattr(item, "title", None) or "unknown"


def _extract_assistant_text(items: list[dict]) -> str:
    """Best-effort extraction of the last assistant text from persisted run items."""
    for item in reversed(items):
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = []
            for piece in content:
                if isinstance(piece, dict):
                    text = piece.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
            joined = "".join(parts).strip()
            if joined:
                return joined
    return ""


@router.post("/chat/sessions")
async def api_v1_chat_session_create(request: Request):
    from opencmo.web import chat_sessions
    body_bytes = await request.body()
    account_id = await get_request_account_id(request)
    try:
        body = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    raw_project_id = body.get("project_id")
    project_id: int | None = None
    if raw_project_id is not None:
        try:
            project_id = int(raw_project_id)
        except (TypeError, ValueError):
            return JSONResponse({"error": "project_id must be an integer"}, status_code=400)
        project = await storage.get_project(project_id, account_id=account_id)
        if not project:
            return JSONResponse({"error": "Project not found"}, status_code=404)

    session_id = await chat_sessions.create_session(project_id=project_id, account_id=account_id)
    return JSONResponse({"session_id": session_id, "project_id": project_id}, status_code=201)


@router.get("/chat/sessions")
async def api_v1_chat_sessions_list(request: Request):
    from opencmo.web import chat_sessions
    account_id = await get_request_account_id(request)
    sessions = await chat_sessions.list_sessions(account_id=account_id)
    return JSONResponse(sessions)


@router.get("/chat/sessions/{session_id}/messages")
async def api_v1_chat_session_messages(session_id: str, request: Request):
    from opencmo.web import chat_sessions
    account_id = await get_request_account_id(request)
    messages = await chat_sessions.get_session_messages(session_id, account_id=account_id)
    if messages is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse(messages)


@router.delete("/chat/sessions/{session_id}")
async def api_v1_chat_session_delete(session_id: str, request: Request):
    from opencmo.web import chat_sessions
    account_id = await get_request_account_id(request)
    ok = await chat_sessions.delete_session(session_id, account_id=account_id)
    if not ok:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"ok": True})


_LOCALE_NAMES = {
    "en": "English",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
}

_GLOBAL_CONTENT_MARKERS = (
    "write",
    "draft",
    "generate",
    "create",
    "rewrite",
    "polish",
    "post",
    "thread",
    "tweet",
    "article",
    "launch copy",
    "maker comment",
    "content",
    "文案",
    "写",
    "生成",
    "改写",
    "润色",
    "发帖",
    "帖子",
    "文章",
    "回答",
    "笔记",
)

_STRATEGY_MARKERS = (
    "strategy",
    "plan",
    "distribution",
    "campaign",
    "渠道",
    "策略",
    "规划",
    "分发",
    "矩阵",
)

_MULTI_PLATFORM_MARKERS = (
    "all platforms",
    "multi-channel",
    "cross-channel",
    "comprehensive",
    "full platform",
    "全平台",
    "多平台",
    "全渠道",
    "矩阵",
)

_PLATFORM_SPECS = (
    {
        "agent_attr": "twitter_expert",
        "platform_markers": ("twitter", "twitter/x", "x/", "x平台", "推特", "tweet", "thread", "推文", "线程"),
        "platform_regexes": (r"(?<![a-z0-9])x(?![a-z0-9])",),
        "content_markers": ("tweet", "thread", "推文", "线程"),
    },
    {
        "agent_attr": "linkedin_expert",
        "platform_markers": ("linkedin", "领英"),
        "content_markers": ("post", "帖子", "内容", "文案"),
    },
    {
        "agent_attr": "reddit_expert",
        "platform_markers": ("reddit", "subreddit"),
        "platform_regexes": (r"(?<![a-z0-9])r/[a-z0-9_]+",),
        "content_markers": ("post", "title", "body", "帖子", "发帖", "标题", "正文"),
        "exclude_markers": ("monitor", "scan", "discussion", "comment", "reply", "社区", "监控", "评论", "回复", "讨论"),
    },
    {
        "agent_attr": "producthunt_expert",
        "platform_markers": ("product hunt", "producthunt"),
        "content_markers": ("launch", "tagline", "maker comment", "gallery", "发布", "上线", "slogan"),
    },
    {
        "agent_attr": "zhihu_expert",
        "platform_markers": ("知乎", "zhihu"),
        "content_markers": ("文章", "回答", "问答", "专栏", "标题", "正文"),
    },
    {
        "agent_attr": "xiaohongshu_expert",
        "platform_markers": ("小红书", "xiaohongshu", "red note", "rednote", "xiaohongshu / red"),
        "content_markers": ("笔记", "封面", "正文", "标题", "tags", "标签"),
    },
    {
        "agent_attr": "hackernews_expert",
        "platform_markers": ("hacker news", "hackernews", "show hn"),
        "content_markers": ("show hn", "title", "body", "帖子", "标题", "正文"),
    },
    {
        "agent_attr": "v2ex_expert",
        "platform_markers": ("v2ex",),
        "content_markers": ("帖子", "标题", "正文", "文案"),
    },
    {
        "agent_attr": "juejin_expert",
        "platform_markers": ("掘金", "juejin"),
        "content_markers": ("文章", "标题", "正文", "教程"),
    },
    {
        "agent_attr": "jike_expert",
        "platform_markers": ("即刻", "jike"),
        "content_markers": ("动态", "帖子", "文案", "内容"),
    },
    {
        "agent_attr": "wechat_expert",
        "platform_markers": ("微信公众号", "微信公众", "wechat"),
        "content_markers": ("文章", "标题", "正文", "推文"),
    },
    {
        "agent_attr": "oschina_expert",
        "platform_markers": ("oschina", "开源中国"),
        "content_markers": ("文章", "项目介绍", "帖子", "标题", "正文"),
    },
    {
        "agent_attr": "gitcode_expert",
        "platform_markers": ("gitcode", "csdn"),
        "content_markers": ("文章", "项目介绍", "仓库介绍", "标题", "正文"),
    },
    {
        "agent_attr": "sspai_expert",
        "platform_markers": ("少数派", "sspai"),
        "content_markers": ("文章", "标题", "正文", "评测"),
    },
    {
        "agent_attr": "infoq_expert",
        "platform_markers": ("infoq",),
        "content_markers": ("文章", "标题", "正文", "投稿"),
    },
    {
        "agent_attr": "devto_expert",
        "platform_markers": ("dev.to", "devto"),
        "content_markers": ("article", "post", "title", "body", "文章", "标题", "正文"),
    },
    {
        "agent_attr": "ruanyifeng_expert",
        "platform_markers": ("阮一峰", "周刊投稿", "ruanyifeng"),
        "content_markers": ("投稿", "title", "body", "标题", "正文"),
    },
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _matches_platform(text: str, spec: dict) -> bool:
    if _contains_any(text, tuple(spec.get("platform_markers", ()))):
        return True
    return any(re.search(pattern, text) for pattern in spec.get("platform_regexes", ()))


def _normalize_message_for_routing(message: str) -> str:
    lowered = message.lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _resolve_direct_platform_agent(message: str):
    normalized = _normalize_message_for_routing(message)
    if _contains_any(normalized, _MULTI_PLATFORM_MARKERS):
        return None

    matches = []
    for spec in _PLATFORM_SPECS:
        if _matches_platform(normalized, spec):
            matches.append(spec)
    if len(matches) != 1:
        return None

    spec = matches[0]
    if _contains_any(normalized, tuple(spec.get("exclude_markers", ()))):
        return None

    content_markers = tuple(spec.get("content_markers", ())) + _GLOBAL_CONTENT_MARKERS
    if not _contains_any(normalized, content_markers):
        return None

    if _contains_any(normalized, _STRATEGY_MARKERS) and not _contains_any(normalized, tuple(spec.get("content_markers", ()))):
        return None

    from opencmo.agents import (
        devto_expert,
        gitcode_expert,
        hackernews_expert,
        infoq_expert,
        jike_expert,
        juejin_expert,
        linkedin_expert,
        oschina_expert,
        producthunt_expert,
        reddit_expert,
        ruanyifeng_expert,
        sspai_expert,
        twitter_expert,
        v2ex_expert,
        wechat_expert,
        xiaohongshu_expert,
        zhihu_expert,
    )

    agent_map = {
        "twitter_expert": twitter_expert,
        "linkedin_expert": linkedin_expert,
        "reddit_expert": reddit_expert,
        "producthunt_expert": producthunt_expert,
        "zhihu_expert": zhihu_expert,
        "xiaohongshu_expert": xiaohongshu_expert,
        "hackernews_expert": hackernews_expert,
        "v2ex_expert": v2ex_expert,
        "juejin_expert": juejin_expert,
        "jike_expert": jike_expert,
        "wechat_expert": wechat_expert,
        "oschina_expert": oschina_expert,
        "gitcode_expert": gitcode_expert,
        "sspai_expert": sspai_expert,
        "infoq_expert": infoq_expert,
        "devto_expert": devto_expert,
        "ruanyifeng_expert": ruanyifeng_expert,
    }
    return agent_map[spec["agent_attr"]]


@router.post("/chat")
async def api_v1_chat(request: Request):
    from opencmo.web import chat_sessions
    body = await request.json()
    session_id = body.get("session_id", "")
    message = body.get("message", "").strip()
    account_id = await get_request_account_id(request)
    user_id = get_request_user_id(request)

    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    session = await storage.get_chat_session(session_id, account_id=account_id)
    if session is None:
        return JSONResponse({"error": "Invalid session_id"}, status_code=404)
    input_items = json.loads(session["input_items"])

    if body.get("project_id") is None and session.get("project_id") is not None:
        body["project_id"] = session["project_id"]

    context_item = None
    # Inject project context from knowledge graph
    from opencmo.context import build_project_context, resolve_chat_project
    project_id = await resolve_chat_project(body, account_id=account_id)
    if project_id:
        if not await storage.get_project(project_id, account_id=account_id):
            return JSONResponse({"error": "Project not found"}, status_code=404)
        ctx = await build_project_context(project_id, depth="full")
        if ctx:
            input_items.insert(0, {"role": "system", "content": f"[Project Context]\n{ctx}"})
            context_item = input_items[0]

    # Inject locale-aware system prompt
    locale = body.get("locale", "en")
    lang_name = _LOCALE_NAMES.get(locale, "English")
    locale_prompt = {
        "role": "system",
        "content": f"[Language Preference]\nThe user's interface language is {lang_name}. You MUST respond in {lang_name}. All your output — analysis, recommendations, content drafts, and explanations — should be written in {lang_name}.",
    }
    insert_index = 1 if context_item is not None else 0
    input_items.insert(insert_index, locale_prompt)

    input_items.append({"role": "user", "content": message})

    from opencmo.rag.config import get_settings as get_rag_settings
    from opencmo.rag.integration import content_request, filter_chat_history, no_evidence_message, safe_handoff_filter
    from opencmo.rag.retrieval import evidence_prompt, retrieve, validate_output
    from opencmo.rag.types import RetrievalRequest
    rag_mode = body.get("rag_mode", "auto")
    if rag_mode not in {"auto", "only", "off"}:
        return JSONResponse({"error": "invalid_rag_mode"}, status_code=400)
    rag_enabled = (await get_rag_settings(account_id)).enabled and rag_mode != "off"
    rag_purpose = "content" if content_request(message) else "internal"
    rag_history = json.loads(session['input_items'])
    if rag_enabled:
        rag_history = await filter_chat_history(account_id, session_id, rag_history, rag_purpose,
                                               session.get('project_id'), project_id)
        input_items = ([context_item] if context_item else []) + [locale_prompt] + rag_history + [{"role": "user", "content": message}]

    async def event_stream():
        try:
            from agents import RunConfig, Runner

            from opencmo.agents.cmo import cmo_agent
            from opencmo.marketing_review import review_marketing_output_with_metadata

            selected_agent = _resolve_direct_platform_agent(message) or cmo_agent
            knowledge = None
            evidence_item = None
            run_options = {}
            if rag_enabled or rag_mode == "only":
                yield f"data: {json.dumps({'type': 'retrieval', 'status': 'running'})}\n\n"
                knowledge = await retrieve(RetrievalRequest(account_id, project_id, message, purpose=rag_purpose,
                    mode=rag_mode, history=rag_history))
                if rag_mode == "only" and not knowledge.citations:
                    output = no_evidence_message(locale)
                    saved = json.loads(session['input_items']) + [{"role": "user", "content": message}, {"role": "assistant", "content": output}]
                    await chat_sessions.update_session(session_id, saved, account_id=account_id)
                    yield f"data: {json.dumps({'type': 'done', 'final_output': output, 'citations': [], 'rag_status': knowledge.status})}\n\n"
                    return
                evidence_item = {"role": "user", "content": evidence_prompt(knowledge, only=rag_mode == 'only')}
                input_items.insert(len(input_items) - 1, evidence_item)
                safe_context = evidence_item['content'] if rag_purpose == 'content' else 'Internal source evidence is unavailable after this handoff. Do not infer private source facts.'
                run_options['run_config'] = RunConfig(handoff_input_filter=safe_handoff_filter(message, safe_context), trace_include_sensitive_data=False)
                if rag_purpose == 'internal' and selected_agent is cmo_agent and knowledge.citations:
                    selected_agent = cmo_agent.clone(handoffs=[], tools=[tool for tool in cmo_agent.tools
                        if not getattr(tool, 'name', '').startswith('generate_')])
                if rag_mode == 'only':
                    selected_agent = selected_agent.clone(handoffs=[], tools=[])
            result = Runner.run_streamed(selected_agent, input_items, max_turns=15, **run_options)
            output_chunks: list[str] = []
            stream_timed_out = False
            stream = result.stream_events()
            try:
                while True:
                    timeout = (
                        _STREAM_IDLE_EVENT_TIMEOUT_SECONDS
                        if output_chunks
                        else _STREAM_FIRST_EVENT_TIMEOUT_SECONDS
                    )
                    try:
                        event = await asyncio.wait_for(anext(stream), timeout=timeout)
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        if output_chunks:
                            stream_timed_out = True
                            logger.warning(
                                "Chat stream idle timeout after %.1fs; finalizing partial output "
                                "(session_id=%s, agent=%s)",
                                timeout,
                                session_id,
                                selected_agent.name,
                            )
                            result.cancel()
                            break
                        raise TimeoutError(
                            f"Chat stream timed out before first output after {timeout:.0f}s"
                        )

                    if event.type == "raw_response_event":
                        data = event.data
                        if hasattr(data, "type") and data.type == "response.output_text.delta":
                            delta = data.delta or ""
                            if delta:
                                output_chunks.append(delta)
                            yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
                    elif event.type == "agent_updated_stream_event":
                        yield f"data: {json.dumps({'type': 'agent', 'name': event.new_agent.name})}\n\n"
                    elif event.type == "run_item_stream_event":
                        name = event.name
                        if name == "tool_called":
                            yield f"data: {json.dumps({'type': 'tool_call', 'name': _get_item_name(event.item)})}\n\n"
                        elif name == "tool_output":
                            yield f"data: {json.dumps({'type': 'tool_done'})}\n\n"
                        elif name == "handoff_requested":
                            yield f"data: {json.dumps({'type': 'handoff', 'target': _get_item_name(event.item)})}\n\n"
                        elif name == "handoff_occured":
                            yield f"data: {json.dumps({'type': 'handoff_done'})}\n\n"
                        elif name == "tool_search_called":
                            yield f"data: {json.dumps({'type': 'tool_search'})}\n\n"
                        elif name == "tool_search_output_created":
                            yield f"data: {json.dumps({'type': 'tool_search_done'})}\n\n"
                        elif name == "message_output_created":
                            yield f"data: {json.dumps({'type': 'message_created'})}\n\n"
                        elif name == "reasoning_item_created":
                            yield f"data: {json.dumps({'type': 'reasoning'})}\n\n"
            finally:
                await stream.aclose()

            # Stream finished — persist session state
            updated_items = result.to_input_list()
            # Strip injected system prompts (locale + context) before persisting
            injected_contents = {locale_prompt["content"]}
            if context_item:
                injected_contents.add(context_item["content"])
            if evidence_item:
                injected_contents.add(evidence_item["content"])
                injected_contents.add(safe_context)
            updated_items = [item for item in updated_items if not (isinstance(item, dict)
                and isinstance(item.get('content'), str) and item['content'] in injected_contents)]
            while (
                updated_items
                and isinstance(updated_items[0], dict)
                and updated_items[0].get("role") == "system"
                and updated_items[0].get("content") in injected_contents
            ):
                updated_items = updated_items[1:]
            agent_name = result.last_agent.name if result.last_agent else "CMO Agent"
            raw_output = ""
            if isinstance(result.final_output, str):
                raw_output = result.final_output.strip()
            if not raw_output and output_chunks:
                raw_output = "".join(output_chunks).strip()
            if not raw_output:
                raw_output = _extract_assistant_text(updated_items)
            try:
                review_result = await asyncio.wait_for(
                    review_marketing_output_with_metadata(
                        agent_name=agent_name,
                        user_message=message,
                        output_text=raw_output,
                    ),
                    timeout=_MARKETING_REVIEW_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                logger.warning(
                    "Marketing review skipped after failure/timeout (session_id=%s, agent=%s): %s",
                    session_id,
                    agent_name,
                    exc,
                )
                review_result = {
                    "final_output": raw_output,
                    "review_applied": False,
                    "profile": None,
                    "weak_points": [],
                }
            final_output = review_result["final_output"]
            citations = []
            if knowledge:
                final_output, citations = await validate_output(final_output, knowledge, account_id)
            assistant_updated = False
            for item in reversed(updated_items):
                if isinstance(item, dict) and item.get("role") == "assistant":
                    item["content"] = final_output
                    assistant_updated = True
                    break
            if final_output and not assistant_updated:
                updated_items.append({"role": "assistant", "content": final_output})
            await chat_sessions.update_session(session_id, updated_items, account_id=account_id)
            if knowledge and knowledge.citations:
                from opencmo.rag.store import put_message_evidence
                await put_message_evidence(session_id, final_output, knowledge.retrieval_id)
            await storage.record_usage_event(
                account_id,
                "ai_chat",
                user_id=user_id,
                project_id=project_id,
                metadata={"session_id": session_id, "agent_name": agent_name},
            )
            yield f"data: {json.dumps({'type': 'done', 'agent_name': agent_name, 'final_output': final_output, 'review_applied': review_result['review_applied'], 'review_profile': review_result['profile'], 'review_weak_points': review_result['weak_points'], 'stream_timed_out': stream_timed_out, 'citations': citations, 'retrieval_id': knowledge.retrieval_id if knowledge else None, 'rag_status': knowledge.status if knowledge else 'disabled'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
