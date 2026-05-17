"""SQLite storage layer for persistent scan data.

This package re-exports all public functions from its submodules so that
existing code using ``from opencmo import storage`` followed by
``storage.some_function()`` continues to work unchanged.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Patch propagation: tests use ``patch.object(storage, "_DB_PATH", ...)``
# which sets the attribute on *this* module.  We need that change to land
# on ``_db._DB_PATH`` so that ``get_db()`` picks up the patched path.
# ---------------------------------------------------------------------------
import sys as _sys

from opencmo.storage import _db as _db_module

# Expose internal DB helpers (tests patch _DB_PATH and _SCHEMA_READY_FOR)
from opencmo.storage._db import (
    _SCHEMA,
    ensure_db,
    get_db,
)

# --- Accounts / sessions / trial usage ---
from opencmo.storage.accounts import (
    SESSION_COOKIE_NAME,
    authenticate_user,
    check_daily_scan_quota,
    check_monthly_report_quota,
    check_project_quota,
    create_session,
    create_user_with_account,
    delete_session,
    extend_account_trial,
    get_account,
    get_admin_account_id,
    get_admin_summary,
    get_session_context,
    get_signup_mode,
    get_trial_config,
    get_usage_status,
    get_user_account,
    get_user_by_id,
    hash_password,
    record_usage_event,
    set_account_status,
    update_account_quota,
    verify_password,
)

# --- AI Models (Provider config + smart failover) ---
from opencmo.storage.ai_models import (
    add_ai_model,
    claim_quota,
    delete_ai_model,
    get_ai_model,
    list_ai_models,
    update_ai_model,
)

# --- Approvals ---
from opencmo.storage.approvals import (
    create_approval,
    create_approval_with_source,
    get_approval,
    list_approvals,
    update_approval_status,
)

# --- Blog Drafts ---
from opencmo.storage.blog_drafts import (
    count_blog_drafts,
    create_blog_draft,
    get_blog_draft,
    get_blog_drafts_by_task,
    list_blog_drafts,
    update_blog_draft,
)

# --- Brand Kit ---
from opencmo.storage.brand_kit import (
    build_brand_kit_prompt,
    get_brand_kit,
    upsert_brand_kit,
)

# --- Campaigns ---
from opencmo.storage.campaigns import (
    add_campaign_artifact,
    create_campaign_run,
    get_campaign_run,
    list_campaign_runs,
    update_campaign_status,
)

# --- Chat sessions ---
from opencmo.storage.chat import (
    clear_chat_sessions,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    update_chat_session,
)

# --- Competitors ---
from opencmo.storage.competitors import (
    add_competitor,
    add_competitor_keyword,
    batch_list_competitor_keywords,
    get_competitor,
    list_competitor_keywords,
    list_competitors,
    remove_competitor,
)

# --- Discussions ---
from opencmo.storage.discussions import (
    get_discussion_snapshots,
    get_tracked_discussions,
    save_discussion_snapshot,
    upsert_tracked_discussion,
)

# --- GEO tools (citability / crawler / brand presence) ---
from opencmo.storage.geo_tools import (
    get_ai_crawler_history,
    get_brand_presence_history,
    get_citability_history,
    save_ai_crawler_scan,
    save_brand_presence_scan,
    save_citability_scan,
)

# --- GitHub Leads ---
from opencmo.storage.github import (
    batch_update_enrichment,
    batch_upsert_github_leads,
    count_github_leads,
    create_discovery_run,
    delete_github_leads,
    get_github_lead,
    get_github_lead_stats,
    get_unenriched_leads,
    list_discovery_runs,
    list_github_leads,
    update_discovery_run,
    update_lead_outreach,
    update_lead_score,
    upsert_github_lead,
)

# --- GitHub stats cache (Built-in-open block) ---
from opencmo.storage.github_stats_cache import (
    get_cached_github_stats,
    set_cached_github_stats,
)

# --- Graph expansion ---
from opencmo.storage.graph import (
    add_expansion_edge,
    add_expansion_node,
    fix_stale_expansions,
    get_expansion,
    get_frontier_nodes,
    get_graph_data,
    get_min_unexplored_wave,
    get_or_create_expansion,
    mark_node_explored,
    reset_expansion,
    seed_expansion_nodes,
    seed_node_if_expansion_exists,
    update_expansion,
)

# --- Insights + autopilot ---
from opencmo.storage.insights import (
    count_recent_autopilot_approvals,
    get_insights_summary,
    get_pending_actionable_insights,
    is_insight_duplicate,
    is_project_autopilot_enabled,
    list_insights,
    mark_all_insights_read,
    mark_insight_read,
    save_insight,
    snapshot_project_metrics,
    update_insight_execution,
)

# --- Scheduled jobs ---
from opencmo.storage.jobs import (
    add_scheduled_job,
    get_scheduled_job,
    list_scheduled_jobs,
    remove_scheduled_job,
    update_job_last_run,
    update_scheduled_job,
)

# --- Projects ---
from opencmo.storage.projects import (
    delete_project,
    ensure_project,
    find_project_by_identity,
    find_projects_by_brand,
    get_project,
    list_projects,
    update_project,
)

# --- Reports ---
from opencmo.storage.reports import (
    create_report_bundle,
    get_latest_report,
    get_latest_reports,
    get_report,
    list_reports,
    normalize_report_locale,
)

# --- Scan runs / findings / recommendations ---
from opencmo.storage.scan_runs import (
    add_scan_run_step,
    create_scan_run,
    fail_scan_run_by_task_id,
    get_latest_monitoring_summary,
    get_scan_run_by_task_id,
    get_task_findings,
    get_task_findings_by_project,
    get_task_recommendations,
    list_scan_runs_by_monitor,
    replace_scan_artifacts,
    update_scan_run,
)

# --- Scans (SEO / GEO / Community) ---
from opencmo.storage.scans import (
    SCAN_DEDUPE_WINDOW_SECONDS,
    get_community_history,
    get_geo_history,
    get_latest_scans,
    get_previous_scans,
    get_seo_history,
    save_community_scan,
    save_geo_scan,
    save_seo_scan,
    scan_params_hash,
    scan_window_start,
)

# --- SERP tracking ---
from opencmo.storage.serp import (
    add_tracked_keyword,
    get_all_serp_latest,
    get_serp_history,
    get_tracked_keyword,
    list_tracked_keywords,
    remove_tracked_keyword,
    save_serp_snapshot,
)

# --- Settings ---
from opencmo.storage.settings import (
    delete_setting,
    get_setting,
    set_setting,
)

# --- Site stats ---
from opencmo.storage.site_stats import (
    get_site_counter,
    increment_site_counter,
)

# --- Email verification codes ---
from opencmo.storage.verifications import (
    DEFAULT_RESEND_COOLDOWN_SECONDS,
    DEFAULT_HOURLY_SEND_LIMIT,
    consume_code as consume_verification_code,
    create_code as create_verification_code,
    is_user_verified,
    last_send_at as last_verification_send_at,
    mark_user_verified,
    recent_send_count as recent_verification_send_count,
)

# --- Waitlist (hosted version signups) ---
from opencmo.storage.waitlist import (
    add_to_waitlist,
    count_waitlist,
    is_valid_email,
)


def __getattr__(name: str):
    if name == "_DB_PATH":
        return _db_module._DB_PATH
    if name == "_SCHEMA_READY_FOR":
        return _db_module._SCHEMA_READY_FOR
    raise AttributeError(f"module 'opencmo.storage' has no attribute {name!r}")


# Called by ``setattr(storage, "_DB_PATH", value)`` — i.e. when unittest.mock
# restores the original value as well as when it patches.
_PROPAGATED_ATTRS = {"_DB_PATH", "_SCHEMA_READY_FOR"}

_original_module = _sys.modules[__name__]


class _PatchableModule(type(_original_module)):
    """Module subclass that propagates attribute writes to _db."""
    def __setattr__(self, name, value):
        if name in _PROPAGATED_ATTRS:
            setattr(_db_module, name, value)
        super().__setattr__(name, value)

    def __getattr__(self, name):
        if name in _PROPAGATED_ATTRS:
            return getattr(_db_module, name)
        raise AttributeError(f"module 'opencmo.storage' has no attribute {name!r}")


_sys.modules[__name__].__class__ = _PatchableModule


__all__ = [
    # _db
    "_DB_PATH", "_SCHEMA", "_SCHEMA_READY_FOR", "ensure_db", "get_db",
    # ai_models
    "add_ai_model", "claim_quota", "delete_ai_model",
    "get_ai_model", "list_ai_models", "update_ai_model",
    # accounts
    "SESSION_COOKIE_NAME", "authenticate_user", "check_daily_scan_quota",
    "check_monthly_report_quota", "check_project_quota", "create_session",
    "create_user_with_account", "delete_session", "extend_account_trial",
    "get_account", "get_admin_account_id", "get_admin_summary",
    "get_session_context", "get_signup_mode", "get_trial_config",
    "get_usage_status", "get_user_account", "get_user_by_id",
    "hash_password", "record_usage_event", "set_account_status",
    "update_account_quota", "verify_password",
    # projects
    "ensure_project", "update_project", "get_project", "list_projects",
    "find_projects_by_brand", "find_project_by_identity", "delete_project",
    # scans
    "save_seo_scan", "save_geo_scan", "save_community_scan",
    "get_seo_history", "get_geo_history", "get_community_history",
    "get_latest_scans", "get_previous_scans",
    "scan_params_hash", "scan_window_start", "SCAN_DEDUPE_WINDOW_SECONDS",
    # discussions
    "upsert_tracked_discussion", "save_discussion_snapshot",
    "get_tracked_discussions", "get_discussion_snapshots",
    # jobs
    "add_scheduled_job", "list_scheduled_jobs", "get_scheduled_job",
    "remove_scheduled_job", "update_scheduled_job", "update_job_last_run",
    # serp
    "add_tracked_keyword", "get_tracked_keyword", "list_tracked_keywords",
    "remove_tracked_keyword", "save_serp_snapshot", "get_serp_history", "get_all_serp_latest",
    # scan_runs
    "create_scan_run", "list_scan_runs_by_monitor", "update_scan_run",
    "fail_scan_run_by_task_id", "get_scan_run_by_task_id",
    "add_scan_run_step", "replace_scan_artifacts",
    "get_task_findings", "get_task_findings_by_project",
    "get_task_recommendations", "get_latest_monitoring_summary",
    # chat
    "create_chat_session", "list_chat_sessions", "get_chat_session",
    "update_chat_session", "delete_chat_session", "clear_chat_sessions",
    # settings
    "get_setting", "set_setting", "delete_setting",
    # site stats
    "get_site_counter", "increment_site_counter",
    # waitlist
    "add_to_waitlist", "count_waitlist", "is_valid_email",
    # email verification codes
    "DEFAULT_RESEND_COOLDOWN_SECONDS", "DEFAULT_HOURLY_SEND_LIMIT",
    "consume_verification_code", "create_verification_code",
    "is_user_verified", "last_verification_send_at",
    "mark_user_verified", "recent_verification_send_count",
    # github stats cache
    "get_cached_github_stats", "set_cached_github_stats",
    # approvals
    "create_approval", "get_approval", "list_approvals",
    "update_approval_status", "create_approval_with_source",
    # competitors
    "add_competitor", "list_competitors", "get_competitor",
    "remove_competitor", "add_competitor_keyword", "list_competitor_keywords",
    "batch_list_competitor_keywords",
    # graph
    "get_or_create_expansion", "get_expansion", "update_expansion",
    "seed_expansion_nodes", "get_min_unexplored_wave", "get_frontier_nodes",
    "mark_node_explored", "add_expansion_node", "add_expansion_edge",
    "reset_expansion", "seed_node_if_expansion_exists", "fix_stale_expansions",
    "get_graph_data",
    # campaigns
    "create_campaign_run", "add_campaign_artifact", "update_campaign_status",
    "get_campaign_run", "list_campaign_runs",
    # insights
    "save_insight", "is_insight_duplicate", "list_insights",
    "mark_insight_read", "mark_all_insights_read", "get_insights_summary",
    "get_pending_actionable_insights", "update_insight_execution",
    "snapshot_project_metrics", "is_project_autopilot_enabled",
    "count_recent_autopilot_approvals",
    # geo_tools
    "save_citability_scan", "get_citability_history",
    "save_ai_crawler_scan", "get_ai_crawler_history",
    "save_brand_presence_scan", "get_brand_presence_history",
    # reports
    "create_report_bundle", "list_reports", "get_report",
    "get_latest_report", "get_latest_reports", "normalize_report_locale",
    # brand_kit
    "get_brand_kit", "upsert_brand_kit", "build_brand_kit_prompt",
    # github
    "upsert_github_lead", "batch_upsert_github_leads", "get_github_lead",
    "list_github_leads", "count_github_leads", "update_lead_outreach",
    "update_lead_score", "batch_update_enrichment", "get_unenriched_leads",
    "delete_github_leads", "create_discovery_run", "update_discovery_run",
    "list_discovery_runs", "get_github_lead_stats",
    # blog_drafts
    "create_blog_draft", "update_blog_draft", "get_blog_draft",
    "list_blog_drafts", "get_blog_drafts_by_task", "count_blog_drafts",
]
