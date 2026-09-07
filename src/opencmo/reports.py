"""AI CMO report generation for strategic briefs and periodic reports."""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from opencmo import storage
from opencmo.opportunities import build_project_opportunity_snapshot

logger = logging.getLogger(__name__)

_REPORT_MODEL_DEFAULT = "gpt-5.4"
_PERIODIC_WINDOW_DAYS = 7
_REPORT_LLM_TIMEOUT_SECONDS = 300.0
_CHART_ASSET_SRC_RE = re.compile(r"^/api/v1/report-assets/[a-f0-9]{32}\.svg$")
_CHART_ASSET_REF_RE = re.compile(r"/api/v1/report-assets/[a-f0-9]{32}\.svg")
_REPORT_LANGUAGE_INSTRUCTIONS = {
    "en": "Language requirement: write the final report in English.",
    "zh": "语言要求：最终报告必须使用简体中文。",
    "ja": "Language requirement: write the final report in Japanese.",
    "ko": "Language requirement: write the final report in Korean.",
    "es": "Language requirement: write the final report in Spanish.",
}
_REPORT_STRUCTURE_LABELS = {
    "en": {
        "conclusion": "Bottom Line",
        "toc": "Table of Contents",
        "charts": "Charts at a Glance",
        "background": "Context and Decision Criteria",
        "strategy": "Strategic Recommendations and Action Roadmap",
        "title_suffix": "Strategic Analysis",
    },
    "zh": {
        "conclusion": "先说结论",
        "toc": "目录",
        "charts": "数据图表速览",
        "background": "背景与判断口径",
        "strategy": "战略建议与行动路线图",
        "title_suffix": "深度战略分析",
    },
    "ja": {
        "conclusion": "まず結論",
        "toc": "目次",
        "charts": "データチャート概観",
        "background": "背景と判断基準",
        "strategy": "戦略提言とアクションロードマップ",
        "title_suffix": "戦略分析",
    },
    "ko": {
        "conclusion": "결론 먼저",
        "toc": "목차",
        "charts": "데이터 차트 한눈에 보기",
        "background": "배경과 판단 기준",
        "strategy": "전략 제안 및 실행 로드맵",
        "title_suffix": "전략 분석",
    },
    "es": {
        "conclusion": "Conclusión Primero",
        "toc": "Índice",
        "charts": "Resumen Visual de Datos",
        "background": "Contexto y Criterios de Evaluación",
        "strategy": "Recomendaciones Estratégicas y Hoja de Ruta",
        "title_suffix": "Análisis Estratégico",
    },
}
_REPORT_EMPTY_CHARTS_TEXT = {
    "en": "Insufficient data; no chart was generated.",
    "zh": "当前数据不足，未生成图表。",
    "ja": "データが不足しているため、チャートは生成されませんでした。",
    "ko": "현재 데이터가 부족하여 차트를 생성하지 못했습니다.",
    "es": "No se generó ningún gráfico porque los datos son insuficientes.",
}
_REPORT_SYSTEM_COMMON = (
    "你是 AI CMO（首席营销官），拥有完整的多智能体营销系统：SEO审计专家、GEO(AI搜索可见性)分析师、"
    "SERP排名追踪器、社区舆情监控(Reddit/HN/Dev.to/知乎/V2EX/掘金等)、AI引文可信度(Citability)评估引擎、"
    "AI爬虫检测模块、品牌数字足迹(Brand Presence)扫描器、竞品知识图谱、以及Insights洞察引擎。"
    "以下事实包(facts)是上述所有智能体在真实运行中采集到的一手数据。\n\n"
    "【打分与量纲规范（百分制）】\n"
    "- 系统所有核心健康度指标必须使用严格的 **百分制 (0-100分)** 进行评价和展示：\n"
    "  - `seo_health_score` (0-100): 综合了技术基础与页面质量的 SEO 评分。\n"
    "  - `geo_score` (0-100): 综合了提及率与情感倾向的 AI 可见性评分。\n"
    "  - `engagement_score` (0-100): 经过算法归一化的社区讨论相对潜力和热度。\n"
    "- 事实包中的 `raw_score` (如 16,525) 代表平台的**绝对物理流量**（播放量/点赞数等），绝对**不能**被用作“评分”，而应解读为具体的“流量表现”与“增长短板”进行交叉对比（例如流量极大但搜索增长极低）。\n\n"
    "核心原则：\n"
    "1. 你必须对事实包中的每一类数据进行深入解读，不能遗漏任何智能体的产出。\n"
    "2. 不要使用含糊的“分数”表述，必须明确说是“SEO百分制健康度”、“社区原始流量表现”等，且不可偏离事实数据。\n"
    "3. 不是简单罗列数据，而是像真正的 CMO 那样做业务推演——高流量为何不能转化为高排名？对增长有什么影响？应该怎么做？\n"
    "4. 不要虚构数据；某个维度数据缺失时，明确标注并说明获取方法。\n"
    "5. 报告要足够深入和详实，像一份面向CEO/投资人级别的商业分析文档。\n"
)
_REPORT_EVIDENCE_DISCIPLINE = (
    "【事实纪律】\n"
    "- 先写已确认事实，再写推断，最后写建议。\n"
    "- 你的表达必须区分：事实 / 推断 / 建议。\n"
    "- 缺失时必须明确标注，不得补造数字、案例、竞品结论或增长结果。\n"
    "- 当样本稀疏时，降低语气强度，并说明结论的置信度边界。\n"
)


def _normalize_report_locale(locale: str | None) -> str:
    return storage.normalize_report_locale(locale)


def _report_language_instruction(locale: str | None) -> str:
    normalized = _normalize_report_locale(locale)
    return _REPORT_LANGUAGE_INSTRUCTIONS.get(normalized, _REPORT_LANGUAGE_INSTRUCTIONS["zh"])


def _report_structure_labels(locale: str | None) -> dict[str, str]:
    normalized = _normalize_report_locale(locale)
    return _REPORT_STRUCTURE_LABELS.get(normalized, _REPORT_STRUCTURE_LABELS["zh"])


def _empty_report_charts_text(locale: str | None) -> str:
    normalized = _normalize_report_locale(locale)
    return _REPORT_EMPTY_CHARTS_TEXT.get(normalized, _REPORT_EMPTY_CHARTS_TEXT["zh"])


def _compose_report_system_prompt(*sections: str, locale: str = "zh") -> str:
    language_instruction = _report_language_instruction(locale)
    return "".join((_REPORT_SYSTEM_COMMON, _REPORT_EVIDENCE_DISCIPLINE, language_instruction, "\n\n", *sections))


def _json_dump(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _filter_window(items: list[dict], field: str, start: datetime, end: datetime | None = None) -> list[dict]:
    result: list[dict] = []
    for item in items:
        timestamp = _parse_ts(item.get(field))
        if timestamp and timestamp >= start and (end is None or timestamp <= end):
            result.append(item)
    return result


def _safe_delta(latest, previous):
    if latest is None or previous is None:
        return None
    return latest - previous


def _score_percent(value) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if 0 <= num <= 1:
        return num * 100
    return num


def _rank_label(position: int | None) -> str:
    if position is None:
        return "未排名"
    return f"#{position}"


def _classify_findings(findings: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    validated: list[dict] = []
    environment_limitations: list[dict] = []
    hypotheses: list[dict] = []
    for finding in findings:
        metadata = finding.get("metadata") or {}
        status = metadata.get("status", "likely")
        if status == "environment_limitation":
            environment_limitations.append(finding)
        elif status == "hypothesis":
            hypotheses.append(finding)
        else:
            validated.append(finding)
    return validated, environment_limitations, hypotheses


def _simple_markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_lines: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            raw_src = image_match.group(2)
            if _CHART_ASSET_SRC_RE.fullmatch(raw_src):
                close_list()
                alt = html.escape(image_match.group(1))
                src = html.escape(raw_src, quote=True)
                html_lines.append(f'<figure><img src="{src}" alt="{alt}" /><figcaption>{alt}</figcaption></figure>')
                continue
        if stripped.startswith("### "):
            close_list()
            html_lines.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            close_list()
            html_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            close_list()
            html_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{html.escape(stripped[2:])}</li>")
            continue
        close_list()
        html_lines.append(f"<p>{html.escape(stripped)}</p>")

    close_list()
    return "\n".join(html_lines)


def _normalize_report_headings(markdown_text: str) -> str:
    """Keep report heading hierarchy to H1/H2/H3 only."""
    lines: list[str] = []
    seen_h1 = False
    for raw_line in markdown_text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", raw_line)
        if not match:
            lines.append(raw_line.rstrip())
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if level == 1 and not seen_h1:
            seen_h1 = True
            lines.append(f"# {title}")
        elif level == 1:
            lines.append(f"## {title}")
        elif level == 2:
            lines.append(f"## {title}")
        else:
            lines.append(f"### {title}")
    return "\n".join(lines).strip()


def _insert_after_named_section(markdown_text: str, section_name: str, section: str) -> str:
    """Insert section after a named H2 block, falling back to after the first H2."""
    lines = markdown_text.splitlines()
    h2_indices = [idx for idx, line in enumerate(lines) if line.startswith("## ")]
    insert_at = None
    for position, idx in enumerate(h2_indices):
        title = lines[idx][3:].strip()
        if title == section_name or title.startswith(f"{section_name} "):
            insert_at = h2_indices[position + 1] if position + 1 < len(h2_indices) else len(lines)
            break
    if insert_at is None and len(h2_indices) >= 2:
        insert_at = h2_indices[1]
    elif insert_at is None and len(lines) >= 1 and lines[0].startswith("# "):
        insert_at = 1
    elif insert_at is None:
        insert_at = 0
    return "\n".join([*lines[:insert_at], "", section.strip(), "", *lines[insert_at:]]).strip()


def _insert_after_first_section(markdown_text: str, section: str) -> str:
    return _insert_after_named_section(markdown_text, "", section)


def _postprocess_human_report_content(content: str, charts_markdown: str, *, locale: str = "zh") -> str:
    content = _normalize_report_headings(content)
    if _CHART_ASSET_REF_RE.search(content):
        return content
    labels = _report_structure_labels(locale)
    chart_body = charts_markdown or _empty_report_charts_text(locale)
    lines = content.splitlines()
    chart_section_names = {labels["charts"], _REPORT_STRUCTURE_LABELS["zh"]["charts"]}
    for idx, line in enumerate(lines):
        if line.startswith("## ") and any(section_name in line for section_name in chart_section_names):
            return "\n".join([*lines[: idx + 1], "", chart_body.strip(), "", *lines[idx + 1 :]]).strip()
    chart_section = f"## {labels['charts']}\n\n{chart_body}"
    return _insert_after_named_section(content, labels["toc"], chart_section)


def _prepare_report_charts(kind: str, facts: dict, meta: dict, *, locale: str = "zh") -> tuple[dict, dict, str]:
    """Generate deterministic charts and return facts/meta copies enriched for prompts."""
    enriched_facts = dict(facts)
    enriched_meta = dict(meta)
    try:
        from opencmo.report_charts import build_report_charts, charts_to_markdown

        charts = build_report_charts(kind, facts, meta, locale=locale)
        charts_markdown = charts_to_markdown(charts, locale=locale) if charts else _empty_report_charts_text(locale)
        enriched_facts["report_charts"] = [chart.to_meta() | {"markdown": chart.markdown} for chart in charts]
        enriched_facts["report_charts_markdown"] = charts_markdown
        enriched_meta["charts"] = [chart.to_meta() for chart in charts]
        enriched_meta["chart_count"] = len(charts)
        return enriched_facts, enriched_meta, charts_markdown
    except Exception as exc:
        logger.exception("Report chart generation failed for %s", kind)
        enriched_meta["chart_error"] = str(exc) or exc.__class__.__name__
        charts_markdown = _empty_report_charts_text(locale)
        enriched_facts["report_charts"] = []
        enriched_facts["report_charts_markdown"] = charts_markdown
        enriched_meta["charts"] = []
        enriched_meta["chart_count"] = 0
        return enriched_facts, enriched_meta, charts_markdown


async def _generate_llm_markdown(system_prompt: str, user_prompt: str, *, model_override: str | None = None) -> str:
    """Generate markdown with the configured LLM."""
    from opencmo import llm

    api_key = await llm.get_key_async("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    timeout = await _get_report_timeout_seconds()
    return await llm.chat_completion(
        system_prompt, user_prompt,
        temperature=0.5,
        timeout=timeout,
        model_override=model_override,
    )


async def _generate_llm_markdown_with_empty_retry(
    system_prompt: str,
    user_prompt: str,
    *,
    primary_model: str,
) -> tuple[str, str | None]:
    """Generate markdown and retry once on the same model when the content is empty."""
    content = await _generate_llm_markdown(system_prompt, user_prompt, model_override=primary_model)
    if content.strip():
        return content, None

    retry_content = await _generate_llm_markdown(
        system_prompt,
        user_prompt,
        model_override=primary_model,
    )
    if retry_content.strip():
        return retry_content, primary_model
    raise RuntimeError("LLM returned empty report content.")


async def _get_runtime_setting(key: str, default: str | None = None) -> str | None:
    from opencmo import llm
    return await llm.get_key_async(key, default)


async def _get_report_model() -> str:
    from opencmo import llm
    return await llm.get_model()


async def _get_report_timeout_seconds() -> float:
    raw_value = await _get_runtime_setting(
        "OPENCMO_REPORT_LLM_TIMEOUT_SECONDS",
        str(_REPORT_LLM_TIMEOUT_SECONDS),
    )
    try:
        timeout = float(raw_value or _REPORT_LLM_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        return _REPORT_LLM_TIMEOUT_SECONDS
    return max(1.0, timeout)


async def _get_recent_recommendations(
    project_id: int,
    limit: int = 6,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    db = await storage.get_db()
    try:
        where = ["r.project_id = ?"]
        params: list[object] = [project_id]
        if start is not None:
            where.append("rec.created_at >= ?")
            params.append(start.isoformat(timespec="seconds"))
        if end is not None:
            where.append("rec.created_at <= ?")
            params.append(end.isoformat(timespec="seconds"))
        params.append(limit)
        cursor = await db.execute(
            """SELECT rec.domain, rec.priority, rec.owner_type, rec.action_type,
                      rec.title, rec.summary, rec.rationale, rec.created_at
               FROM scan_recommendations rec
               JOIN scan_runs r ON r.id = rec.run_id
               WHERE """ + " AND ".join(where) + """
               ORDER BY r.id DESC,
                 CASE rec.priority
                   WHEN 'high' THEN 0
                   WHEN 'medium' THEN 1
                   ELSE 2
                 END,
                 rec.id
               LIMIT ?""",
            tuple(params),
        )
        rows = await cursor.fetchall()
        return [
            {
                "domain": row[0],
                "priority": row[1],
                "owner_type": row[2],
                "action_type": row[3],
                "title": row[4],
                "summary": row[5],
                "rationale": row[6],
                "created_at": row[7],
            }
            for row in rows
        ]
    finally:
        await db.close()


async def _get_recent_findings(
    project_id: int,
    limit: int = 6,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    db = await storage.get_db()
    try:
        where = ["r.project_id = ?"]
        params: list[object] = [project_id]
        if start is not None:
            where.append("f.created_at >= ?")
            params.append(start.isoformat(timespec="seconds"))
        if end is not None:
            where.append("f.created_at <= ?")
            params.append(end.isoformat(timespec="seconds"))
        params.append(limit)
        cursor = await db.execute(
            """SELECT f.domain, f.severity, f.title, f.summary, f.metadata_json, f.created_at
               FROM scan_findings f
               JOIN scan_runs r ON r.id = f.run_id
               WHERE """ + " AND ".join(where) + """
               ORDER BY r.id DESC,
                 CASE f.severity
                   WHEN 'critical' THEN 0
                   WHEN 'warning' THEN 1
                   ELSE 2
                 END,
                 f.id
               LIMIT ?""",
            tuple(params),
        )
        rows = await cursor.fetchall()
        return [
            {
                "domain": row[0],
                "severity": row[1],
                "title": row[2],
                "summary": row[3],
                "metadata": json.loads(row[4] or "{}"),
                "created_at": row[5],
            }
            for row in rows
        ]
    finally:
        await db.close()


async def _get_recent_approvals(project_id: int, start: datetime, end: datetime | None = None) -> list[dict]:
    db = await storage.get_db()
    try:
        cursor = await db.execute(
            """SELECT id, approval_type, status, title, agent_name, created_at, decided_at
               FROM approvals
               WHERE project_id = ?
               ORDER BY created_at DESC, id DESC
               LIMIT 20""",
            (project_id,),
        )
        rows = await cursor.fetchall()
        approvals = [
            {
                "id": row[0],
                "approval_type": row[1],
                "status": row[2],
                "title": row[3],
                "agent_name": row[4],
                "created_at": row[5],
                "decided_at": row[6],
            }
            for row in rows
        ]
    finally:
        await db.close()
    return _filter_window(approvals, "created_at", start, end)


async def _build_strategic_facts(project_id: int, *, locale: str = "zh") -> tuple[dict, dict]:
    project = await storage.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    # Parallel data aggregation - Phase 1 optimization
    (
        keywords,
        competitors,
        latest,
        previous,
        monitoring,
        findings,
        recommendations,
        previous_human,
        insights,
        citability_history,
        ai_crawler_history,
        brand_presence_history,
        discussions,
        serp_latest,
        opportunity_snapshot,
    ) = await asyncio.gather(
        storage.list_tracked_keywords(project_id),
        storage.list_competitors(project_id),
        storage.get_latest_scans(project_id),
        storage.get_previous_scans(project_id),
        storage.get_latest_monitoring_summary(project_id),
        storage.get_task_findings_by_project(project_id, limit=15),
        _get_recent_recommendations(project_id, limit=12),
        storage.get_latest_report(project_id, "strategic", "human", locale=locale),
        storage.list_insights(project_id=project_id, limit=15),
        storage.get_citability_history(project_id, limit=3),
        storage.get_ai_crawler_history(project_id, limit=3),
        storage.get_brand_presence_history(project_id, limit=3),
        storage.get_tracked_discussions(project_id),
        storage.get_all_serp_latest(project_id),
        build_project_opportunity_snapshot(project_id),
    )
    findings, environment_limitations, hypothesis_findings = _classify_findings(findings)

    # Fetch competitor keywords in parallel using batch query
    competitor_cards: list[dict] = []
    if competitors:
        competitor_ids = [comp["id"] for comp in competitors]
        competitor_keywords_map = await storage.batch_list_competitor_keywords(competitor_ids)
        for competitor in competitors:
            competitor_cards.append({
                **competitor,
                "keywords": competitor_keywords_map.get(competitor["id"], []),
            })
    else:
        competitor_cards = []

    # Try to get knowledge graph data for competitive landscape
    graph_data = None
    try:
        expansion = await storage.get_expansion(project_id)
        if expansion:
            graph_data = await storage.get_graph_data(expansion["id"])
    except Exception:
        pass  # graph may not exist yet

    # Recent approvals (last 30 days for strategic context)
    approvals_window = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    recent_approvals = await _get_recent_approvals(project_id, approvals_window)

    seo_score = latest.get("seo", {}).get("score") if latest.get("seo") else None
    geo_score = latest.get("geo", {}).get("score") if latest.get("geo") else None
    community_hits = latest.get("community", {}).get("total_hits") if latest.get("community") else None
    seo_delta = _safe_delta(
        latest.get("seo", {}).get("score") if latest.get("seo") else None,
        previous.get("seo", {}).get("score") if previous and previous.get("seo") else None,
    )
    geo_delta = _safe_delta(
        latest.get("geo", {}).get("score") if latest.get("geo") else None,
        previous.get("geo", {}).get("score") if previous and previous.get("geo") else None,
    )

    strengths: list[str] = []
    if seo_score is not None and seo_score >= 0.8:
        strengths.append(f"SEO 基础分达到 {round(seo_score * 100)}%，站点健康度较稳。")
    if geo_score is not None and geo_score >= 60:
        strengths.append(f"GEO 得分 {geo_score}/100，AI 可见性已经形成基础。")
    if community_hits:
        strengths.append(f"社区侧已发现 {community_hits} 条相关讨论，有可运营的自然信号。")
    if serp_latest:
        ranked = [item for item in serp_latest if item.get("position")]
        if ranked:
            strengths.append(f"已有 {len(ranked)}/{len(serp_latest)} 个关键词进入搜索结果。")
    if citability_history:
        avg = _score_percent(citability_history[0].get("avg_score"))
        if avg is not None and avg >= 60:
            strengths.append(f"AI 引文可信度评分 {round(avg)}%，内容被 AI 引用的潜力较高。")
    if brand_presence_history:
        fp = brand_presence_history[0].get("footprint_score")
        if fp and fp >= 60:
            strengths.append(f"品牌数字足迹分 {fp}/100，线上存在感已初步建立。")
    if ai_crawler_history:
        blocked = ai_crawler_history[0].get("blocked_count", 0)
        total = ai_crawler_history[0].get("total_crawlers", 14)
        if blocked == 0:
            strengths.append(f"全部 {total} 个 AI 爬虫均已放行，对 AI 索引完全开放。")

    risks: list[str] = []
    if seo_score is None:
        risks.append("SEO 基线仍不完整。")
    elif seo_score < 0.7:
        risks.append(f"SEO 基础分仅 {round(seo_score * 100)}%，技术面仍拖后腿。")
    if geo_score is None:
        risks.append("GEO 数据缺失，AI 渠道认知仍是盲区。")
    elif geo_score < 45:
        risks.append(f"GEO 得分 {geo_score}/100，AI 平台认知偏弱。")
    if not competitor_cards:
        risks.append("竞品画像仍然稀薄。")
    if findings:
        risks.append(f"最近一次监控仍有 {len(findings)} 条待处理发现。")
    if environment_limitations:
        risks.append(f"有 {len(environment_limitations)} 条监控限制来自环境或 provider 异常，需谨慎解读。")
    if citability_history:
        avg = _score_percent(citability_history[0].get("avg_score"))
        if avg is not None and avg < 40:
            risks.append(f"AI 引文可信度评分仅 {round(avg)}%，内容结构化程度不足以被 AI 引用。")
    if ai_crawler_history:
        blocked = ai_crawler_history[0].get("blocked_count", 0)
        if blocked > 3:
            risks.append(f"有 {blocked} 个 AI 爬虫被 robots.txt 屏蔽，AI 索引受限。")
    if brand_presence_history:
        fp = brand_presence_history[0].get("footprint_score")
        if fp is not None and fp < 30:
            risks.append(f"品牌数字足迹分仅 {fp}/100，线上存在感薄弱。")
    # Flag critical/warning insights as risks
    critical_insights = [i for i in insights if i.get("severity") in ("critical", "warning")]
    for ins in critical_insights[:3]:
        risks.append(f"[{ins['severity'].upper()}] {ins['title']}：{ins['summary']}")

    change_lines: list[str] = []
    if previous_human:
        if seo_delta is not None:
            change_lines.append(f"SEO 相比上一版变动 {seo_delta:+.2f}。")
        if geo_delta is not None:
            change_lines.append(f"GEO 相比上一版变动 {geo_delta:+.0f}。")
        if serp_latest:
            top_keyword = serp_latest[0]
            change_lines.append(
                f"当前首个跟踪关键词 {top_keyword['keyword']} 排名 {_rank_label(top_keyword.get('position'))}。"
            )

    facts = {
        "project": project,
        "keywords": keywords,
        "competitors": competitor_cards,
        "latest_scans": latest,
        "previous_scans": previous,
        "monitoring_summary": monitoring,
        "findings": findings,
        "environment_limitations": environment_limitations,
        "hypothesis_findings": hypothesis_findings,
        "recommendations": recommendations,
        "insights": insights,
        "citability": citability_history,
        "ai_crawler": ai_crawler_history,
        "brand_presence": brand_presence_history,
        "discussions": discussions[:12],
        "serp_latest": serp_latest,
        "opportunities": opportunity_snapshot["opportunities"],
        "cluster_summary": opportunity_snapshot["cluster_summary"],
        "graph_data": graph_data,
        "recent_approvals": recent_approvals,
        "strengths": strengths,
        "risks": risks,
        "change_lines": change_lines,
        "previous_report_excerpt": (previous_human["content"][:2000] if previous_human else ""),
        # --- Aliases consumed by report_pipeline._DIMENSIONS ---
        # The deep-report pipeline references different key names; expose both
        # so the LLM-facing slicing sees SEO/GEO/community/serp data instead of
        # silently slotting in None.
        "seo_latest": (latest or {}).get("seo"),
        "geo_latest": (latest or {}).get("geo"),
        "community_latest": (latest or {}).get("community"),
        "serp_snapshots": serp_latest,
        "ai_crawler_history": ai_crawler_history,
        "citability_history": citability_history,
        "brand_presence_history": brand_presence_history,
        "insights_history": insights,
        "approvals": recent_approvals,
    }
    data_sources = [
        latest.get("seo"), latest.get("geo"), latest.get("community"),
        serp_latest, keywords, competitor_cards, insights,
        citability_history, ai_crawler_history, brand_presence_history,
        discussions, graph_data,
    ]
    sample_count = sum(1 for item in data_sources if item)
    meta = {
        "sample_count": sample_count,
        "total_data_sources": len(data_sources),
        "low_sample": sample_count < 3,
        "facts_summary": (
            f"{len(keywords)} 个关键词, {len(competitor_cards)} 个竞品, "
            f"{len(findings)} 条已验证发现, {len(recommendations)} 条建议, "
            f"{len(insights)} 条洞察, {len(discussions)} 条社区讨论, "
            f"{len(citability_history)} 条引文分析, {len(ai_crawler_history)} 条爬虫检测, "
            f"{len(brand_presence_history)} 条品牌存在感分析"
        ),
        "change_count": len(change_lines),
        "locale": _normalize_report_locale(locale),
    }
    return facts, meta


async def _build_periodic_facts(
    project_id: int,
    *,
    now: datetime | None = None,
    window_days: int = _PERIODIC_WINDOW_DAYS,
) -> tuple[dict, dict]:
    project = await storage.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
    elif now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    window_start_dt = now - timedelta(days=window_days)
    window_start = window_start_dt.isoformat(timespec="seconds")
    window_end = now.isoformat(timespec="seconds")

    # Parallel data aggregation - Phase 1 optimization
    (
        keywords,
        seo_history_raw,
        geo_history_raw,
        community_history_raw,
        discussions_raw,
        recent_approvals,
        recommendations,
        findings,
        serp_latest_raw,
        insights_raw,
        citability_history_raw,
        ai_crawler_history_raw,
        brand_presence_history_raw,
        opportunity_snapshot,
    ) = await asyncio.gather(
        storage.list_tracked_keywords(project_id),
        storage.get_seo_history(project_id, limit=30),
        storage.get_geo_history(project_id, limit=30),
        storage.get_community_history(project_id, limit=30),
        storage.get_tracked_discussions(project_id),
        _get_recent_approvals(project_id, window_start_dt, now),
        _get_recent_recommendations(project_id, limit=12, start=window_start_dt, end=now),
        _get_recent_findings(project_id, limit=15, start=window_start_dt, end=now),
        storage.get_all_serp_latest(project_id),
        storage.list_insights(project_id=project_id, limit=15),
        storage.get_citability_history(project_id, limit=5),
        storage.get_ai_crawler_history(project_id, limit=5),
        storage.get_brand_presence_history(project_id, limit=5),
        build_project_opportunity_snapshot(project_id),
    )
    findings, environment_limitations, hypothesis_findings = _classify_findings(findings)

    # Apply time window filtering
    seo_history = _filter_window(seo_history_raw, "scanned_at", window_start_dt, now)
    geo_history = _filter_window(geo_history_raw, "scanned_at", window_start_dt, now)
    community_history = _filter_window(community_history_raw, "scanned_at", window_start_dt, now)
    discussions = _filter_window(discussions_raw, "last_checked_at", window_start_dt, now)
    serp_latest = _filter_window(serp_latest_raw, "checked_at", window_start_dt, now)
    insights = _filter_window(insights_raw, "created_at", window_start_dt, now)
    citability_history = _filter_window(citability_history_raw, "scanned_at", window_start_dt, now)
    ai_crawler_history = _filter_window(ai_crawler_history_raw, "scanned_at", window_start_dt, now)
    brand_presence_history = _filter_window(brand_presence_history_raw, "scanned_at", window_start_dt, now)

    data_sources = [seo_history, geo_history, community_history, serp_latest,
                    insights, citability_history, ai_crawler_history, brand_presence_history]
    sample_count = sum(1 for items in data_sources if items)
    low_sample = sample_count < 2

    seo_delta = None
    if len(seo_history) >= 2:
        seo_delta = _safe_delta(seo_history[0].get("score_performance"), seo_history[-1].get("score_performance"))
    geo_delta = None
    if len(geo_history) >= 2:
        geo_delta = _safe_delta(geo_history[0].get("geo_score"), geo_history[-1].get("geo_score"))
    community_delta = None
    if len(community_history) >= 2:
        community_delta = _safe_delta(community_history[0].get("total_hits"), community_history[-1].get("total_hits"))

    top_changes: list[str] = []
    if seo_history:
        current = seo_history[0].get("score_performance")
        if current is not None:
            line = f"最新 SEO 分数 {round(current * 100)}%"
            if seo_delta is not None:
                line += f"，窗口内变动 {seo_delta:+.2f}"
            top_changes.append(line + "。")
    if geo_history:
        current = geo_history[0].get("geo_score")
        if current is not None:
            line = f"最新 GEO 分数 {current}/100"
            if geo_delta is not None:
                line += f"，窗口内变动 {geo_delta:+.0f}"
            top_changes.append(line + "。")
    if community_history:
        current = community_history[0].get("total_hits")
        if current is not None:
            line = f"最新社区命中 {current} 条"
            if community_delta is not None:
                line += f"，窗口内变动 {community_delta:+.0f}"
            top_changes.append(line + "。")
    if serp_latest:
        ranked = [item for item in serp_latest if item.get("position")]
        top_changes.append(f"当前共有 {len(ranked)}/{len(serp_latest)} 个关键词进入自然搜索结果。")
    if citability_history:
        avg = _score_percent(citability_history[0].get("avg_score"))
        if avg is not None:
            top_changes.append(f"AI 引文可信度评分 {round(avg)}%。")
    if brand_presence_history:
        fp = brand_presence_history[0].get("footprint_score")
        if fp is not None:
            top_changes.append(f"品牌数字足迹分 {fp}/100。")
    if low_sample:
        top_changes.insert(0, "样本稀疏，以下结论仅供方向判断。")

    facts = {
        "project": project,
        "window_start": window_start,
        "window_end": window_end,
        "keywords": keywords,
        "seo_history": seo_history,
        "geo_history": geo_history,
        "community_history": community_history,
        "discussions": discussions[:12],
        "serp_latest": serp_latest,
        "opportunities": opportunity_snapshot["opportunities"],
        "cluster_summary": opportunity_snapshot["cluster_summary"],
        "findings": findings,
        "environment_limitations": environment_limitations,
        "hypothesis_findings": hypothesis_findings,
        "recommendations": recommendations,
        "insights": insights,
        "citability": citability_history,
        "ai_crawler": ai_crawler_history,
        "brand_presence": brand_presence_history,
        "recent_approvals": recent_approvals,
        "top_changes": top_changes[:5],
        # Aliases consumed by report_pipeline._DIMENSIONS.
        "seo_latest": seo_history[0] if seo_history else None,
        "geo_latest": geo_history[0] if geo_history else None,
        "community_latest": community_history[0] if community_history else None,
        "serp_snapshots": serp_latest,
        "citability_history": citability_history,
        "ai_crawler_history": ai_crawler_history,
        "brand_presence_history": brand_presence_history,
        "insights_history": insights,
        "approvals": recent_approvals,
    }
    meta = {
        "sample_count": sample_count,
        "total_data_sources": len(data_sources),
        "low_sample": low_sample,
        "facts_summary": (
            f"SEO 样本 {len(seo_history)}, GEO 样本 {len(geo_history)}, "
            f"Community 样本 {len(community_history)}, SERP 关键词 {len(serp_latest)}, "
            f"跟踪关键词 {len(keywords)} 个, "
            f"已验证发现 {len(findings)} 条, 环境限制 {len(environment_limitations)} 条, "
            f"洞察 {len(insights)} 条, 引文分析 {len(citability_history)} 条, "
            f"爬虫检测 {len(ai_crawler_history)} 条, 品牌存在感 {len(brand_presence_history)} 条"
        ),
        "window_days": window_days,
        "window_start": window_start,
        "window_end": window_end,
    }
    return facts, meta


def _failed_report_payload(meta: dict, model: str, *, used_pipeline: bool, llm_error: str, pipeline_error: str | None = None) -> dict:
    record_meta = {
        **meta,
        "used_fallback": False,
        "used_pipeline": used_pipeline,
        "model": model,
        "llm_error": llm_error,
    }
    if pipeline_error:
        record_meta["pipeline_error"] = pipeline_error
    return {
        "generation_status": "failed",
        "content": "",
        "content_html": "",
        "meta": record_meta,
    }


def _prompts(
    kind: str,
    audience: str,
    facts: dict,
    meta: dict,
    previous_exists: bool,
    *,
    locale: str = "zh",
) -> tuple[str, str]:
    project = facts["project"]
    locale = _normalize_report_locale(locale)
    labels = _report_structure_labels(locale)
    if kind == "strategic" and audience == "human":
        system = _compose_report_system_prompt(
            "你的任务是生成一份极其深入的战略分析报告。输出 Markdown，报告总长度应在 2000-4000 字之间。\n\n"
            "【标题与可视化硬性要求】\n"
            "- `#` 只用于报告总标题，`##` 只用于一级章节，`###` 只用于二级小节，禁止使用 `####` 或更深标题。\n"
            f"- 报告开头必须先给结论：`# 报告标题` 后第一个一级章节必须是 `## {labels['conclusion']}`。\n"
            f"- `## {labels['conclusion']}` 必须用 3-5 条短段落或 bullet 直接说明核心判断、最大风险、第一优先级行动；不要写背景铺垫。\n"
            f"- 第二个一级章节必须是 `## {labels['toc']}`，列出后续章节标题，让读者先知道报告结构。\n"
            f"- `## {labels['toc']}` 后再进入图表、背景、诊断和行动计划。\n"
            "- 必须保留并解释输入中提供的真实图表 Markdown，不能修改图表链接、标题或图表数字。\n"
            f"- 必须包含 `## {labels['charts']}`，且必须放在 `## {labels['toc']}` 后；每张图后解释：图表说明、业务含义、数据限制。\n"
            "- 一级章节标题要清晰可扫读，二级标题必须是结论型标题，不要写空泛标题。\n\n"
            "严格按以下阅读顺序生成，先让读者抓结论，再展开论证：\n\n"
            f"## {labels['conclusion']}\n"
            "  - 一句话定义项目当前所处的增长阶段和最关键业务影响\n"
            "  - 给出 3-5 个最高价值判断，每条必须区分事实 / 推断 / 建议\n"
            "  - 最后点明第一优先级行动\n\n"
            f"## {labels['toc']}\n"
            "  - 列出后续一级章节\n\n"
            f"## {labels['charts']}\n"
            "  - 引用输入中的图表，并解释每张图的业务含义与限制\n\n"
            f"## {labels['background']}\n"
            "  - 从 SEO分数、GEO分数、品牌足迹分、AI引文可信度等多维指标定义判断框架\n"
            "  - 如果有历史报告，对比版本差异并给出趋势判断\n\n"
            "## 核心竞争力与优势护城河解析 (Core Competencies)\n"
            "  - 逐一解读每个优势信号背后的商业含义\n"
            "  - 分析 AI 引文可信度(Citability)和 AI爬虫放行状态对「被AI推荐」的影响\n"
            "  - 社区讨论中的正面信号与品牌数字足迹的协同效应\n"
            "  - SERP排名中已拿下的关键词意味着什么流量机会\n\n"
            "## 风险扫描与增长短板预警 (Risk Scanning)\n"
            "  - 逐一深入解读每个风险信号的根因和潜在影响\n"
            "  - 结合 Insights 洞察系统中的 warning/critical 级别告警做交叉验证\n"
            "  - 评估哪些风险会直接影响获客转化，哪些是长期隐患\n"
            "  - 给出风险优先级排序\n\n"
            "## 竞品全景与流量抢占分析 (Competitive Landscape)\n"
            "  - 如果有竞品数据和知识图谱数据，做详细的竞品对比分析\n"
            "  - 关键词重叠与差异化机会\n"
            "  - SERP中的直接竞争态势\n"
            "  - 在AI搜索(GEO)中的相对位置\n"
            "  - 如果竞品数据不完善，指出如何补充\n\n"
            "## 目标受众与社区舆论洞察 (Audience & Community Sentiment)\n"
            "  - 分析社区讨论(discussions)的主题和情绪基调\n"
            "  - 从社区流量来源(Reddit、HN、知乎、V2EX等)推断用户画像\n"
            "  - 审批队列中的内容产出动势如何\n"
            "  - 品牌在各个平台上的存在感差异\n\n"
            f"## {labels['strategy']} (CMO Strategy & Actions)\n"
            "  - 基于以上全部分析给出 3-5 个可执行的战略方向\n"
            "  - 每个方向要具体到：由哪个Agent执行、预期指标变化、实施优先级\n"
            "  - 给一个清晰的「30天行动路线图」\n"
            "  - 标明需要人工介入的关键节点\n"
            "\n再次强调：即使事实包中的部分摘要是中文，也要先理解并翻译/改写，最终报告只能使用目标语言。\n",
            locale=locale,
        )
        user = (
            f"项目：{project['brand_name']} ({project['category']})\n"
            f"目标网址：{project['url']}\n"
            f"版本是否已有历史报告：{previous_exists}\n"
            f"数据来源覆盖度：{meta.get('sample_count', 0)}/{meta.get('total_data_sources', 0)} 个数据源有数据\n"
            f"摘要元数据：{_json_dump(meta)}\n\n"
            f"=== 必须引用的真实图表（由后端基于事实包生成，不得改写数字或链接）===\n"
            f"{facts.get('report_charts_markdown', _empty_report_charts_text(locale))}\n\n"
            f"=== 完整事实包（来自所有智能体的采集结果）===\n{_json_dump(facts)}"
        )
        return system, user

    if kind == "strategic" and audience == "agent":
        system = _compose_report_system_prompt(
            "输出 Markdown，这是给 AI Agent 和执行团队的可执行行动简报。结构固定为：\n\n"
            "## 1. 本周必做（P0）\n"
            "   - 列出 2-3 个最高优先级任务\n"
            "   - 每个任务必须写清：动作、负责人（若适用）、完成标准\n"
            "   - 用自然语言写任务，不要使用占位编号、虚构命令或不存在的系统能力\n\n"
            "## 2. 本月推进节奏（P1-P2）\n"
            "   - 按 Week 1-4 给出推进节奏或里程碑\n"
            "   - 每周写清目标、依赖项、预期产出\n\n"
            "## 3. 所需配置与依赖\n"
            "   - 列出需要补齐的配置、数据源或人工决策\n"
            "   - 如果系统里没有明确可调用的命令或自动化入口，就描述能力需求，不要编造 CLI\n\n"
            "## 4. 检查点与风险信号\n"
            "   - 给出 Day 1/7/14 的检查点或观察信号\n"
            "   - 只有当事实包里已有明确数字时才允许写目标值；否则写成定性检查项\n\n"
            "## 5. Agent 可自动执行 vs 需人工介入\n"
            "   - 明确区分哪些动作可由现有 Agent 直接执行，哪些需要人工批准、外部账号或额外工具\n\n"
            "## 6. 关键数据快照\n"
            "   - 只引用事实包里已经存在的核心 KPI，不要补造新的量化指标\n"
            "\n再次强调：即使事实包中的部分摘要是中文，也要先理解并翻译/改写，最终简报只能使用目标语言。\n",
            locale=locale,
        )
        user = f"项目战略事实包：\n{_json_dump({'meta': meta, 'facts': facts})}"
        return system, user

    if kind == "periodic" and audience == "human":
        system = _compose_report_system_prompt(
            "你的任务是生成一份深度周报。输出 Markdown，报告总长度应在 1500-3000 字之间。\n\n"
            "【标题与可视化硬性要求】\n"
            "- `#` 只用于报告总标题，`##` 只用于一级章节，`###` 只用于二级小节，禁止使用 `####` 或更深标题。\n"
            f"- 报告开头必须先给结论：`# 报告标题` 后第一个一级章节必须是 `## {labels['conclusion']}`。\n"
            f"- `## {labels['conclusion']}` 必须用 3-5 条短段落或 bullet 直接说明本周最大变化、最大风险、下周第一优先级；不要写背景铺垫。\n"
            f"- 第二个一级章节必须是 `## {labels['toc']}`，列出后续章节标题，让读者先知道报告结构。\n"
            f"- `## {labels['toc']}` 后再进入图表、趋势诊断和行动计划。\n"
            "- 必须保留并解释输入中提供的真实图表 Markdown，不能修改图表链接、标题或图表数字。\n"
            f"- 必须包含 `## {labels['charts']}`，且必须放在 `## {labels['toc']}` 后；每张图后解释：图表说明、业务含义、数据限制。\n"
            "- 少于 2 个时间点的指标不能写成趋势，只能写成当前快照。\n\n"
            "严格按以下阅读顺序生成，先让读者抓结论，再展开论证：\n\n"
            f"## {labels['conclusion']}\n"
            "  - 直接给出本周 3-5 个最高价值判断，每条必须区分事实 / 推断 / 建议\n"
            "  - 最后点明下周第一优先级行动\n\n"
            f"## {labels['toc']}\n"
            "  - 列出后续一级章节\n\n"
            f"## {labels['charts']}\n"
            "  - 引用输入中的图表，并解释每张图的业务含义与限制\n\n"
            "## 本周最重要的变化 (Top Changes)\n"
            "  - 列出 3-5 个最重要的变化，每个变化不仅要说「发生了什么」，还要解释「为什么重要」「对增长意味着什么」\n"
            "  - 如果有 AI引文可信度、品牌数字足迹的变化也要覆盖\n\n"
            "## 多维度趋势深度分析 (SEO/GEO/SERP/Community/Citability/Brand Presence)\n"
            "  - 对每个有数据的维度做趋势诊断（上升/下降/持平），并分析走势背后的原因\n"
            "  - 做跨维度关联分析：例如 SEO得分下降是否影响了SERP排名？社区讨论增加是否推动了GEO可见性？\n"
            "  - AI爬虫放行状态有无变化？AI引文可信度的趋势如何？\n\n"
            "## 本周新增风险与亮点 (Risks & Wins)\n"
            "  - 结合 Insights 洞察系统的告警做深入解读\n"
            "  - 风险要给出具体影响评估和缓解建议\n"
            "  - 亮点要说明如何扩大战果\n\n"
            "## 竞品与市场信号变化 (Competitive & Market Signals)\n"
            "  - 社区讨论中有无竞品相关的新动向\n"
            "  - SERP排名中竞品的排名变化\n"
            "  - 审批队列中的内容产出情况\n\n"
            "## 下周战略焦点与执行计划 (Next Week Strategy)\n"
            "  - 给出 3-5 个具体的下周行动项\n"
            "  - 每个行动项标明负责的Agent和预期结果\n"
            "  - 标注需要人工决策的事项\n\n"
            "样本稀疏时，必须在报告开头显式标注置信度。\n"
            "\n再次强调：即使事实包中的部分摘要是中文，也要先理解并翻译/改写，最终报告只能使用目标语言。",
            locale=locale,
        )
        user = (
            f"项目：{project['brand_name']} ({project['category']})\n"
            f"统计窗口：{meta.get('window_start', '未知')} 到 {meta.get('window_end', '未知')}\n"
            f"数据来源覆盖度：{meta.get('sample_count', 0)}/{meta.get('total_data_sources', 0)} 个数据源有数据\n"
            f"元数据：{_json_dump(meta)}\n\n"
            f"=== 必须引用的真实图表（由后端基于事实包生成，不得改写数字或链接）===\n"
            f"{facts.get('report_charts_markdown', _empty_report_charts_text(locale))}\n\n"
            f"=== 完整事实包（来自所有智能体的采集结果）===\n{_json_dump(facts)}"
        )
        return system, user

    # periodic / agent
    system = _compose_report_system_prompt(
        "输出 Markdown，保持像给执行 Agent 的周度行动简报。结构固定为：\n"
        "1. 项目与置信度\n"
        "2. 本周关键指标快照\n"
        "3. 下周重点目标\n"
        "4. 优先方向与 Agent 分工\n"
        "5. 护栏与禁止事项\n"
        "\n再次强调：即使事实包中的部分摘要是中文，也要先理解并翻译/改写，最终简报只能使用目标语言。",
        locale=locale,
    )
    user = f"周期报告事实包：\n{_json_dump({'meta': meta, 'facts': facts})}"
    return system, user


async def _generate_report_record(
    *,
    kind: str,
    audience: str,
    facts: dict,
    meta: dict,
    previous_exists: bool,
    locale: str = "zh",
    on_progress=None,
) -> dict:
    used_pipeline = False
    used_fallback = False
    llm_error = None
    pipeline_error = None
    model = await _get_report_model()
    report_model = model
    content = ""
    charts_markdown = ""
    chart_asset_ids: list[str] = []

    if audience == "human":
        facts, meta, charts_markdown = _prepare_report_charts(kind, facts, meta, locale=locale)
        chart_asset_ids = [
            chart["asset_id"]
            for chart in meta.get("charts", [])
            if isinstance(chart.get("asset_id"), str)
        ]

    # Human reports use the deep multi-agent pipeline;
    # Agent briefs stay single-call (they need to be concise).
    if audience == "human":
        try:
            from opencmo.report_pipeline import run_deep_report_pipeline

            content = await run_deep_report_pipeline(
                facts, meta, previous_exists, kind=kind,
                locale=locale,
                on_progress=on_progress,
            )
            used_pipeline = True
            if not content.strip():
                raise RuntimeError("Pipeline returned empty report.")
            content = _postprocess_human_report_content(content, charts_markdown, locale=locale)
        except Exception as pipeline_exc:
            pipeline_error = str(pipeline_exc) or pipeline_exc.__class__.__name__
            logger.warning(
                "Deep pipeline failed for %s/%s, falling back to single-call: %s",
                kind, audience, pipeline_exc,
            )
            # Fallback to single-call LLM
            try:
                system_prompt, user_prompt = _prompts(kind, audience, facts, meta, previous_exists, locale=locale)
                content, fallback_model = await _generate_llm_markdown_with_empty_retry(
                    system_prompt,
                    user_prompt,
                    primary_model=model,
                )
                used_fallback = True
                if fallback_model:
                    report_model = fallback_model
                content = _postprocess_human_report_content(content, charts_markdown, locale=locale)
            except Exception as exc:
                llm_error = str(exc) or exc.__class__.__name__
                logger.exception("Report generation failed for %s/%s", kind, audience)
                if chart_asset_ids:
                    try:
                        from opencmo.report_charts import delete_chart_assets

                        delete_chart_assets(chart_asset_ids)
                    except Exception:
                        logger.exception("Failed to clean up chart assets for failed %s/%s report", kind, audience)
                return _failed_report_payload(
                    meta,
                    model,
                    used_pipeline=False,
                    llm_error=llm_error,
                    pipeline_error=pipeline_error,
                )
    else:
        # Agent brief — single-call path
        system_prompt, user_prompt = _prompts(kind, audience, facts, meta, previous_exists, locale=locale)
        try:
            content, fallback_model = await _generate_llm_markdown_with_empty_retry(
                system_prompt,
                user_prompt,
                primary_model=model,
            )
            used_fallback = fallback_model is not None
            if fallback_model:
                report_model = fallback_model
        except Exception as exc:
            llm_error = str(exc) or exc.__class__.__name__
            logger.exception("Report generation failed for %s/%s", kind, audience)
            return _failed_report_payload(
                meta,
                model,
                used_pipeline=False,
                llm_error=llm_error,
            )

    record_meta = {
        **meta,
        "used_fallback": used_fallback,
        "used_pipeline": used_pipeline,
        "model": report_model,
    }
    if llm_error:
        record_meta["llm_error"] = llm_error
    if pipeline_error:
        record_meta["pipeline_error"] = pipeline_error

    return {
        "generation_status": "completed",
        "content": content,
        "content_html": _simple_markdown_to_html(content),
        "meta": record_meta,
    }


from opencmo.rag.integration import finalize_generation, section_evidence, with_knowledge


@with_knowledge('internal')
async def _persist_bundle(
    *,
    project_id: int,
    kind: str,
    locale: str,
    source_run_id: int | None,
    window_start: str | None,
    window_end: str | None,
    facts: dict,
    meta: dict,
    on_progress=None,
) -> dict:
    locale = _normalize_report_locale(locale)
    meta = {**meta, "locale": locale}
    previous_human = await storage.get_latest_report(project_id, kind, "human", locale=locale)
    knowledge_context = await section_evidence(f"{facts.get('project', {}).get('brand_name', '')} {kind} report: historical results, customer evidence, marketing case studies")
    if knowledge_context:
        facts = {**facts, 'knowledge_evidence': knowledge_context}
    records = {
        "human": await _generate_report_record(
            kind=kind,
            audience="human",
            facts=facts,
            meta=meta,
            previous_exists=bool(previous_human),
            locale=locale,
            on_progress=on_progress,
        ),
        "agent": await _generate_report_record(
            kind=kind,
            audience="agent",
            facts=facts,
            meta=meta,
            previous_exists=bool(previous_human),
            locale=locale,
        ),
    }
    for record in records.values():
        content, evidence_meta = await finalize_generation(record.get('content', ''))
        if evidence_meta:
            record['content'] = content
            record['content_html'] = _simple_markdown_to_html(content)
            record['meta'] = {**record.get('meta', {}), **evidence_meta}
    created = await storage.create_report_bundle(
        project_id=project_id,
        kind=kind,
        locale=locale,
        source_run_id=source_run_id,
        window_start=window_start,
        window_end=window_end,
        records=records,
    )
    payload = {"kind": kind, "locale": locale}
    payload.update({item["audience"]: item for item in created})
    try:
        from opencmo.rag.ingestion import import_report
        for item in created:
            await import_report(item)
    except Exception:
        logger.warning('Knowledge indexing could not be queued for report bundle')
    return payload


async def generate_strategic_report_bundle(
    project_id: int,
    source_run_id: int | None = None,
    *,
    locale: str = "zh",
    on_progress=None,
) -> dict:
    """Generate and persist the latest strategic report bundle."""
    locale = _normalize_report_locale(locale)
    facts, meta = await _build_strategic_facts(project_id, locale=locale)
    return await _persist_bundle(
        project_id=project_id,
        kind="strategic",
        locale=locale,
        source_run_id=source_run_id,
        window_start=None,
        window_end=None,
        facts=facts,
        meta=meta,
        on_progress=on_progress,
    )


async def generate_periodic_report_bundle(
    project_id: int,
    *,
    source_run_id: int | None = None,
    locale: str = "zh",
    now: datetime | None = None,
    window_days: int = _PERIODIC_WINDOW_DAYS,
    on_progress=None,
) -> dict:
    """Generate and persist the latest periodic report bundle."""
    locale = _normalize_report_locale(locale)
    facts, meta = await _build_periodic_facts(project_id, now=now, window_days=window_days)
    return await _persist_bundle(
        project_id=project_id,
        kind="periodic",
        locale=locale,
        source_run_id=source_run_id,
        window_start=meta["window_start"],
        window_end=meta["window_end"],
        facts=facts,
        meta=meta,
        on_progress=on_progress,
    )
