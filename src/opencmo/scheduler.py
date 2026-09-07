"""Scheduler module — runs periodic scans using APScheduler."""

from __future__ import annotations

import asyncio
import logging
import os

from opencmo import storage
from opencmo.tools.browser_pool import browser_slot

logger = logging.getLogger(__name__)

# APScheduler is an optional dependency
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False

_scheduler: "AsyncIOScheduler | None" = None
_FALSEY_VALUES = {"0", "false", "no", "off"}


def _require_apscheduler():
    if not _HAS_APSCHEDULER:
        raise RuntimeError(
            "APScheduler is required for scheduling. Install with: pip install opencmo[scheduler]"
        )


def is_scheduler_available() -> bool:
    """Return whether APScheduler is installed in this environment."""
    return _HAS_APSCHEDULER


def is_scheduler_enabled() -> bool:
    """Return whether runtime scheduling is enabled."""
    raw = os.environ.get("OPENCMO_ENABLE_SCHEDULER", "1")
    return raw.strip().lower() not in _FALSEY_VALUES


def _job_key(job_id: int) -> str:
    return f"opencmo_job_{job_id}"


async def _maybe_send_email_report(project_id: int, job_type: str, triggered_by: str, *, locale: str = "zh"):
    """Send email report only for (full, cron) runs."""
    if job_type != "full" or triggered_by != "cron":
        return
    try:
        from opencmo.tools.email_report import _get_smtp_config, send_report_impl

        if _get_smtp_config() is None:
            return
        await send_report_impl(project_id, locale=locale)
    except Exception:
        logger.exception("Email report failed for project %d", project_id)


async def run_scheduled_scan(
    project_id: int,
    job_type: str,
    job_id: int | None = None,
    triggered_by: str = "cron",
    locale: str = "zh",
):
    """Execute a scan directly (no LLM), save results to DB.

    Args:
        project_id: The project to scan.
        job_type: One of 'seo', 'geo', 'community', 'full'.
        job_id: Optional scheduled_jobs.id to update last_run_at.
        triggered_by: "cron" (scheduled) or "manual" (CLI).
    """
    project = await storage.get_project(project_id)
    if not project:
        logger.error("Project %d not found, skipping scan", project_id)
        return

    brand = project["brand_name"]
    url = project["url"]
    category = project["category"]

    if job_type in ("seo", "full"):
        try:
            from crawl4ai import AsyncWebCrawler

            from opencmo.tools.seo_audit import (
                _build_report,
                _check_robots_and_sitemap,
                _check_security_headers,
                _compute_seo_health_score,
                _fetch_core_web_vitals,
                _SEOParser,
            )

            async def _crawl():
                async with browser_slot():
                    async with AsyncWebCrawler() as crawler:
                        return await crawler.arun(url=url)

            result = await asyncio.wait_for(_crawl(), timeout=90)
            parser = _SEOParser()
            html = getattr(result, "html", "") or ""
            parser.feed(html)
            cwv, robots_sitemap, security_headers = await asyncio.gather(
                _fetch_core_web_vitals(url),
                _check_robots_and_sitemap(url),
                _check_security_headers(url),
            )
            report = _build_report(
                parser, result, url,
                cwv=cwv, robots_sitemap=robots_sitemap, security_headers=security_headers,
            )
            seo_health_score = _compute_seo_health_score(parser, cwv=cwv, robots_sitemap=robots_sitemap, url=url)
            await storage.save_seo_scan(
                project_id, url, report,
                score_performance=cwv.get("performance") if cwv else None,
                score_lcp=cwv.get("lcp") if cwv else None,
                score_cls=cwv.get("cls") if cwv else None,
                score_tbt=cwv.get("tbt") if cwv else None,
                score_inp=cwv.get("inp") if cwv else None,
                has_robots_txt=robots_sitemap.get("has_robots") if robots_sitemap else None,
                has_sitemap=robots_sitemap.get("has_sitemap") if robots_sitemap else None,
                has_schema_org=bool(parser.schema_types),
                seo_health_score=seo_health_score,
                pagespeed_available=cwv is not None,
                has_hsts=security_headers.get("has_hsts") if security_headers else None,
                has_security_headers=security_headers.get("has_security_headers") if security_headers else None,
                params_hash=storage.scan_params_hash("seo", url),
                window_start=storage.scan_window_start(),
            )
            logger.info("SEO scan saved for project %d", project_id)
        except Exception:
            logger.exception("SEO scan failed for project %d", project_id)

        # SERP tracking (independent — runs even if SEO audit fails)
        try:
            from opencmo.tools.serp_tracker import track_project_keywords

            await track_project_keywords(project_id)
            logger.info("SERP tracking done for project %d", project_id)
        except Exception:
            logger.exception("SERP tracking failed for project %d", project_id)

        # Keyword suggestions (independent — refreshes suggestions each scan)
        try:
            from opencmo.tools.keyword_suggest import suggest_keywords_impl
        except ModuleNotFoundError as exc:
            if exc.name == "opencmo.tools.keyword_suggest":
                logger.debug("Keyword suggestion module not available; skipping for project %d", project_id)
            else:
                logger.exception("Keyword suggestion failed for project %d", project_id)
        except Exception:
            logger.exception("Keyword suggestion failed for project %d", project_id)
        else:
            try:
                await suggest_keywords_impl(project_id, url)
                logger.info("Keyword suggestions updated for project %d", project_id)
            except Exception:
                logger.exception("Keyword suggestion failed for project %d", project_id)

        # AI crawler access check (independent)
        try:
            import json as _json

            from opencmo.tools.ai_crawler_check import _ai_crawler_impl

            data = await _ai_crawler_impl(url)
            await storage.save_ai_crawler_scan(
                project_id, url, data["blocked_count"],
                total_crawlers=data["total_crawlers"],
                has_llms_txt=data["has_llms_txt"],
                results_json=_json.dumps(data["crawler_results"]),
            )
            logger.info("AI crawler scan saved for project %d", project_id)
        except Exception:
            logger.exception("AI crawler scan failed for project %d", project_id)

    if job_type in ("geo", "full"):
        try:
            import json

            from opencmo.tools.geo_providers import (
                GeoAggregatedResult,
                compute_share_of_voice,
                get_enabled_providers,
                reset_brand_aliases,
                set_brand_aliases,
            )
            from opencmo.tools.text_signals import analyze_geo_sentiment

            enabled = get_enabled_providers()
            project_aliases = (project or {}).get("aliases") if project else None
            aliases_token = set_brand_aliases(project_aliases)
            try:
                async def _check_one(provider):
                    try:
                        return provider.name, await provider.check_visibility_multi(brand, category)
                    except Exception as exc:
                        return provider.name, GeoAggregatedResult(
                            platform=provider.name,
                            mentioned=False,
                            total_mention_count=0,
                            best_position_pct=None,
                            per_query_results=[],
                            source_status="error",
                            error=str(exc),
                        )

                pairs = await asyncio.gather(*(_check_one(p) for p in enabled))
                results = {name: agg for name, agg in pairs if agg is not None}
            finally:
                reset_brand_aliases(aliases_token)

            sov = None
            try:
                comp_rows = await storage.list_competitors(project_id)
                competitors_for_sov = [
                    (c["name"], list(c.get("aliases") or [])) for c in comp_rows
                ]
                if competitors_for_sov:
                    sov_snippets = []
                    for agg in results.values():
                        for qr in getattr(agg, "per_query_results", []):
                            if getattr(qr, "content_snippet", "") and getattr(qr, "source_status", "ok") == "ok":
                                sov_snippets.append(qr.content_snippet)
                    sov = compute_share_of_voice(
                        sov_snippets, brand, project_aliases, competitors_for_sov
                    )
            except Exception:
                sov = None

            usable = {name: r for name, r in results.items() if getattr(r, "source_status", "ok") == "ok"}
            crawl_success_rate = len(usable) / len(enabled) if enabled else 0.0
            platforms_mentioned = sum(1 for r in usable.values() if r.mentioned)
            visibility_score = int(platforms_mentioned / len(usable) * 40) if usable else 0
            position_scores = [30 * (1 - r.best_position_pct / 100) for r in usable.values() if r.best_position_pct is not None]
            position_score = int(sum(position_scores) / len(position_scores)) if position_scores else 0
            sentiment_snippets: dict[str, str] = {}
            for name, aggregated in results.items():
                if getattr(aggregated, "source_status", "ok") != "ok":
                    continue
                snippets = [
                    qr.content_snippet
                    for qr in getattr(aggregated, "per_query_results", [])
                    if getattr(qr, "content_snippet", "") and getattr(qr, "source_status", "ok") == "ok"
                ]
                if snippets:
                    sentiment_snippets[name] = "\n".join(snippets)

            sentiment_signal = await analyze_geo_sentiment(brand, sentiment_snippets)
            sentiment_score = sentiment_signal.score
            geo_score = (
                visibility_score + position_score + (sentiment_score or 0)
                if crawl_success_rate > 0
                else None
            )

            payload = {
                name: {
                    "mentioned": r.mentioned,
                    "mention_count": r.total_mention_count,
                    "position_pct": r.best_position_pct,
                    "source_status": getattr(r, "source_status", "ok"),
                    "error": getattr(r, "error", None),
                }
                for name, r in results.items()
            }
            payload["_sentiment"] = {
                "score": sentiment_score,
                "label": sentiment_signal.label,
                "reasoning": sentiment_signal.reasoning,
            }
            platform_json = json.dumps(payload)
            await storage.save_geo_scan(
                project_id, geo_score,
                visibility_score=visibility_score,
                position_score=position_score,
                sentiment_score=sentiment_score,
                crawl_success_rate=crawl_success_rate,
                platform_results_json=platform_json,
                share_of_voice_json=json.dumps(sov) if sov is not None else None,
                params_hash=storage.scan_params_hash(
                    "geo", brand.lower(), category.lower(),
                    sorted(p.name for p in enabled),
                ),
                window_start=storage.scan_window_start(),
            )
            logger.info("GEO scan saved for project %d", project_id)
        except Exception:
            logger.exception("GEO scan failed for project %d", project_id)

        # Citability scan (independent)
        try:
            import json as _json

            from opencmo.tools.citability import _citability_impl

            data = await _citability_impl(url)
            if not data.get("error"):
                await storage.save_citability_scan(
                    project_id, url, data["avg_score"],
                    top_blocks_json=_json.dumps(data["top_blocks"]),
                    bottom_blocks_json=_json.dumps(data["bottom_blocks"]),
                    grade_distribution_json=_json.dumps(data["grade_distribution"]),
                    report_json=_json.dumps(data),
                )
                logger.info("Citability scan saved for project %d", project_id)
        except Exception:
            logger.exception("Citability scan failed for project %d", project_id)

        # Brand presence scan (independent)
        try:
            import json as _json

            from opencmo.tools.brand_presence import _brand_presence_impl

            data = await _brand_presence_impl(brand, url)
            await storage.save_brand_presence_scan(
                project_id, brand, data["footprint_score"],
                platforms_json=_json.dumps(data["platforms"], default=str),
            )
            logger.info("Brand presence scan saved for project %d", project_id)
        except Exception:
            logger.exception("Brand presence scan failed for project %d", project_id)

    # Content frequency check (independent — runs during full scans)
    if job_type == "full":
        try:
            from opencmo.tools.content_frequency import _analyze_content_frequency

            freq_data = await _analyze_content_frequency(url)
            if freq_data.get("has_blog"):
                logger.info(
                    "Content frequency for project %d: %s posts/month (%s)",
                    project_id, freq_data.get("posts_per_month"), freq_data.get("frequency_label"),
                )
        except Exception:
            logger.exception("Content frequency check failed for project %d", project_id)

    if job_type in ("community", "full"):
        try:
            import json

            from opencmo.tools.community import _scan_community_impl

            tracked_keywords = [
                item["keyword"]
                for item in await storage.list_tracked_keywords(project_id)
            ]
            competitors = await storage.list_competitors(project_id)
            competitor_names = [item["name"] for item in competitors]
            competitor_keywords: list[str] = []
            for competitor in competitors:
                competitor_keywords.extend(
                    keyword["keyword"]
                    for keyword in await storage.list_competitor_keywords(competitor["id"])
                )

            raw = await _scan_community_impl(
                brand,
                category,
                tracked_keywords=tracked_keywords,
                competitor_names=competitor_names,
                competitor_keywords=competitor_keywords,
                canonical_url=url,
            )
            data = json.loads(raw)
            total_hits = len(data.get("hits", []))
            await storage.save_community_scan(project_id, total_hits, raw)

            # Track discussions + snapshots (filter out irrelevant noise)
            from opencmo.tools.community_scoring import text_relevance

            for hit in data.get("hits", []):
                if hit.get("source_kind") == "external_search":
                    continue
                # Skip hits with very low text relevance to brand name
                title = hit.get("title", "")
                preview = hit.get("preview", "")
                relevance = text_relevance(brand, title, preview)
                if relevance < 0.05 and (hit.get("engagement_score") or 0) < 5:
                    continue
                try:
                    disc_id = await storage.upsert_tracked_discussion(project_id, hit)
                    await storage.save_discussion_snapshot(
                        disc_id, hit.get("raw_score", 0),
                        hit.get("comments_count", 0),
                        hit.get("engagement_score", 0),
                    )
                except Exception:
                    pass

            logger.info("Community scan saved for project %d", project_id)
        except Exception:
            logger.exception("Community scan failed for project %d", project_id)

    # Update job last_run_at
    if job_id is not None:
        try:
            await storage.update_job_last_run(job_id)
        except Exception:
            pass

    # Detect insights (rule-based, zero LLM cost)
    try:
        from opencmo.insights import detect_insights
        await detect_insights(project_id)
    except Exception:
        logger.exception("Insight detection failed for project %d", project_id)

    # Autopilot: turn insights into content → approval queue
    try:
        from opencmo.autopilot import execute_autopilot
        results = await execute_autopilot(project_id)
        if results:
            logger.info("Autopilot generated %d approvals for project %d", len(results), project_id)
    except Exception:
        logger.exception("Autopilot execution failed for project %d", project_id)

    # Strategic + periodic reports
    if job_type == "full":
        try:
            from opencmo.reports import generate_strategic_report_bundle

            await generate_strategic_report_bundle(project_id, source_run_id=None, locale=locale)
        except Exception:
            logger.exception("Strategic report generation failed for project %d", project_id)

    if job_type == "full" and triggered_by == "cron":
        try:
            from opencmo.reports import generate_periodic_report_bundle

            await generate_periodic_report_bundle(project_id, source_run_id=None, locale=locale)
        except Exception:
            logger.exception("Periodic report generation failed for project %d", project_id)

    # Email report (only for cron + full)
    await _maybe_send_email_report(project_id, job_type, triggered_by, locale=locale)


def get_scheduler() -> "AsyncIOScheduler":
    """Get or create the global scheduler instance."""
    _require_apscheduler()
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def scheduler_status() -> dict:
    """Return scheduler runtime state for health checks."""
    enabled = is_scheduler_enabled()
    if not _HAS_APSCHEDULER:
        return {"installed": False, "enabled": enabled, "running": False, "job_count": 0}

    if not enabled or _scheduler is None:
        return {"installed": True, "enabled": enabled, "running": False, "job_count": 0}

    return {
        "installed": True,
        "enabled": enabled,
        "running": _scheduler.running,
        "job_count": len(_scheduler.get_jobs()),
    }


def sync_job_record(job: dict) -> bool:
    """Reconcile one scheduled job into APScheduler memory state."""
    if not _HAS_APSCHEDULER or not is_scheduler_enabled():
        return False

    scheduler = get_scheduler()
    job_key = _job_key(job["id"])
    if not job["enabled"]:
        if scheduler.get_job(job_key) is not None:
            scheduler.remove_job(job_key)
        return True

    trigger = CronTrigger.from_crontab(job["cron_expr"])
    scheduler.add_job(
        run_scheduled_scan,
        trigger=trigger,
        args=[job["project_id"], job["job_type"], job["id"], "cron", job.get("locale", "zh")],
        id=job_key,
        replace_existing=True,
    )
    return True


def unschedule_job(job_id: int) -> bool:
    """Remove one scheduled job from APScheduler memory state."""
    if not _HAS_APSCHEDULER or _scheduler is None:
        return False

    job_key = _job_key(job_id)
    if _scheduler.get_job(job_key) is None:
        return False

    _scheduler.remove_job(job_key)
    return True


async def load_jobs_from_db():
    """Load all enabled scheduled jobs from DB and add them to the scheduler."""
    if not is_scheduler_enabled():
        return 0
    _require_apscheduler()
    scheduler = get_scheduler()
    scheduler.remove_all_jobs()
    jobs = await storage.list_scheduled_jobs()
    enabled_jobs = 0
    for job in jobs:
        if not job["enabled"]:
            continue
        sync_job_record(job)
        enabled_jobs += 1
    return enabled_jobs


def start_scheduler():
    """Start the scheduler (call after load_jobs_from_db)."""
    if not is_scheduler_enabled():
        return
    _require_apscheduler()
    scheduler = get_scheduler()
    if not scheduler.running:
        from opencmo.rag.ingestion import schedule_maintenance
        scheduler.add_job(schedule_maintenance, 'interval', hours=6, id='knowledge-maintenance', replace_existing=True)
        scheduler.start()


def stop_scheduler():
    """Stop the scheduler if running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
